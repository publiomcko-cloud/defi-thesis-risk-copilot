"""Evaluation-only Ollama adapter with observed model and SSH-tunnel evidence.

The ordinary Ollama provider remains metadata-agnostic. This adapter can only
be created after inspecting a live local SSH forwarding process and querying
the actual Ollama API through that forward. It is never selected for product
routes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import httpx

from app.llm.base import LLMRequest, LLMResponse
from app.llm.providers import OllamaProvider, _ollama_generate_payload, _ollama_response_from_payload
from app.llm.research_gpu_policy import (
    RESEARCH_GPU_EXPECTED_MANIFEST_DIGEST,
    RESEARCH_GPU_EXPECTED_QUANTIZATION,
    RESEARCH_GPU_EXPECTED_WEIGHTS_DIGEST,
    RESEARCH_GPU_MODEL_LAYER_MEDIA_TYPE,
    RESEARCH_GPU_REQUIRED_MODEL,
)


_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SSH_TARGET = re.compile(r"^(?P<user>[A-Za-z0-9_.-]{1,64})@(?P<host>[A-Za-z0-9][A-Za-z0-9.-]{0,252}[A-Za-z0-9])$")
_OLLAMA_VERSION = re.compile(r"^[A-Za-z0-9._+-]{1,64}$")
_MAX_NATIVE_DURATION_NS = 45_000_000_000
RESEARCH_GPU_MANIFEST_EVIDENCE_PATH = Path(__file__).with_name("research_gpu_ollama_manifest.json")


class ResearchGpuAdapterError(ValueError):
    """Runtime model or transport evidence did not satisfy the GPU profile."""


@dataclass(frozen=True)
class SshForwardingEvidence:
    ssh_pid: int
    ssh_target: str
    ssh_port: int
    local_port: int
    known_hosts_sha256: str
    ssh_command_sha256: str

    def to_payload(self) -> dict[str, object]:
        return {
            "ssh_pid": self.ssh_pid,
            "ssh_target": self.ssh_target,
            "ssh_port": self.ssh_port,
            "local_port": self.local_port,
            "known_hosts_sha256": self.known_hosts_sha256,
            "ssh_command_sha256": self.ssh_command_sha256,
        }


@dataclass(frozen=True)
class OllamaRuntimeAttestation:
    server_version: str
    model_name: str
    manifest_digest: str
    weights_digest: str
    weights_layer_media_type: str
    quantization: str
    transport: SshForwardingEvidence
    local_endpoint: str
    verified_at: str
    cold_model_absent_at: str
    loaded_model_names_before_unload: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "server_version": self.server_version,
            "model_name": self.model_name,
            "manifest_digest": self.manifest_digest,
            "weights_digest": self.weights_digest,
            "weights_layer_media_type": self.weights_layer_media_type,
            "quantization": self.quantization,
            "transport_kind": "verified_ssh_local_forward.v1",
            "transport": self.transport.to_payload(),
            "local_endpoint": self.local_endpoint,
            "verified_at": self.verified_at,
            "cold_model_absent_at": self.cold_model_absent_at,
            "loaded_model_names_before_unload": list(self.loaded_model_names_before_unload),
        }


@dataclass(frozen=True)
class OllamaNativeObservation:
    phase: str
    observed_at: str
    load_duration_ns: int | None
    total_duration_ns: int | None
    prompt_eval_duration_ns: int | None
    eval_duration_ns: int | None
    cold_load_confirmed: bool
    native_metrics_valid: bool

    def to_payload(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "observed_at": self.observed_at,
            "load_duration_ns": self.load_duration_ns,
            "total_duration_ns": self.total_duration_ns,
            "prompt_eval_duration_ns": self.prompt_eval_duration_ns,
            "eval_duration_ns": self.eval_duration_ns,
            "cold_load_confirmed": self.cold_load_confirmed,
            "native_metrics_valid": self.native_metrics_valid,
        }


@dataclass(frozen=True)
class OllamaModelIdentity:
    manifest_digest: str
    weights_digest: str
    weights_layer_media_type: str
    quantization: str


def verify_ssh_forwarding_process(
    ssh_pid: int,
    base_url: str,
    *,
    proc_root: Path = Path("/proc"),
) -> SshForwardingEvidence:
    """Verify the actual Linux ssh process and strict local-forward command."""

    if not isinstance(ssh_pid, int) or isinstance(ssh_pid, bool) or ssh_pid <= 1:
        raise ResearchGpuAdapterError("SSH forwarding process identity is invalid")
    endpoint = urlparse(base_url)
    if (
        endpoint.scheme != "http"
        or endpoint.hostname != "127.0.0.1"
        or endpoint.port is None
        or endpoint.username is not None
        or endpoint.password is not None
        or endpoint.query
        or endpoint.fragment
        or endpoint.path not in {"", "/"}
    ):
        raise ResearchGpuAdapterError("Research-GPU Ollama endpoint must be an explicit loopback URL")

    process_dir = proc_root / str(ssh_pid)
    try:
        exe_path = os.readlink(process_dir / "exe")
        stat_data = (process_dir / "stat").read_text()
        cmdline_data = (process_dir / "cmdline").read_bytes()
    except OSError:
        raise ResearchGpuAdapterError("SSH forwarding process cannot be verified") from None
    stat_tail = stat_data.rpartition(")")[2].strip().split()
    if not stat_tail or stat_tail[0] == "Z" or Path(exe_path).name != "ssh":
        raise ResearchGpuAdapterError("Loopback endpoint is not owned by a live SSH process")
    try:
        argv = [part.decode() for part in cmdline_data.split(b"\0") if part]
    except UnicodeDecodeError:
        raise ResearchGpuAdapterError("SSH forwarding command is not valid text") from None
    if not argv or Path(argv[0]).name != "ssh":
        raise ResearchGpuAdapterError("SSH forwarding process command is invalid")

    options: dict[str, str] = {}
    forwarding: str | None = None
    target: str | None = None
    ssh_port = 22
    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg == "-o" and index + 1 < len(argv):
            option = argv[index + 1]
            if "=" in option:
                key, value = option.split("=", 1)
                options[key.lower()] = value
            index += 2
            continue
        if arg == "-L" and index + 1 < len(argv):
            forwarding = argv[index + 1]
            index += 2
            continue
        if arg == "-p" and index + 1 < len(argv):
            try:
                ssh_port = int(argv[index + 1])
            except ValueError:
                raise ResearchGpuAdapterError("SSH forwarding port is invalid") from None
            index += 2
            continue
        if "@" in arg and not arg.startswith("-"):
            target = arg
        index += 1

    required_options = {
        "batchmode": "yes",
        "exitonforwardfailure": "yes",
        "stricthostkeychecking": "yes",
    }
    if any(options.get(key) != value for key, value in required_options.items()):
        raise ResearchGpuAdapterError("SSH forwarding must use batch mode and strict host-key checking")
    known_hosts_value = options.get("userknownhostsfile")
    if not known_hosts_value or known_hosts_value == "/dev/null":
        raise ResearchGpuAdapterError("SSH forwarding must use an explicit known-hosts file")
    known_hosts_path = Path(known_hosts_value).expanduser()
    try:
        known_hosts_bytes = known_hosts_path.read_bytes()
    except OSError:
        raise ResearchGpuAdapterError("SSH known-hosts file is unavailable") from None
    expected_forward = f"127.0.0.1:{endpoint.port}:127.0.0.1:11434"
    if (
        "-N" not in argv
        or "-T" not in argv
        or not any(argv[index : index + 2] == ["-F", "/dev/null"] for index in range(len(argv) - 1))
        or forwarding != expected_forward
        or target is None
        or not _SSH_TARGET.fullmatch(target)
        or not 1 <= ssh_port <= 65535
    ):
        raise ResearchGpuAdapterError("SSH forwarding does not match the authorized Ollama tunnel")

    command_hash = hashlib.sha256(b"\0".join(part.encode() for part in argv)).hexdigest()
    return SshForwardingEvidence(
        ssh_pid=ssh_pid,
        ssh_target=target,
        ssh_port=ssh_port,
        local_port=endpoint.port,
        known_hosts_sha256=hashlib.sha256(known_hosts_bytes).hexdigest(),
        ssh_command_sha256=command_hash,
    )


class VerifiedResearchGpuOllamaProvider(OllamaProvider):
    """Genuine Ollama HTTP adapter restricted to verified public-only GPU runs."""

    privacy_classification = "public_only"

    def __init__(
        self,
        *,
        base_url: str,
        model_manifest_digest: str,
        model_weights_digest: str,
        ssh_pid: int,
        runtime_attestation: OllamaRuntimeAttestation,
    ) -> None:
        super().__init__(base_url, RESEARCH_GPU_REQUIRED_MODEL)
        if (
            model_manifest_digest != RESEARCH_GPU_EXPECTED_MANIFEST_DIGEST
            or not _DIGEST.fullmatch(model_manifest_digest)
        ):
            raise ResearchGpuAdapterError("Verified model manifest digest is invalid")
        if (
            model_weights_digest != RESEARCH_GPU_EXPECTED_WEIGHTS_DIGEST
            or not _DIGEST.fullmatch(model_weights_digest)
        ):
            raise ResearchGpuAdapterError("Verified model weights digest is invalid")
        if (
            runtime_attestation.manifest_digest != model_manifest_digest
            or runtime_attestation.weights_digest != model_weights_digest
        ):
            raise ResearchGpuAdapterError("Verified model identities do not match runtime evidence")
        if runtime_attestation.model_name != RESEARCH_GPU_REQUIRED_MODEL:
            raise ResearchGpuAdapterError("Verified model name does not match the research policy")
        # OllamaProvider exposes artifact_digest as a generic compatibility
        # field. The evaluation binding below stores both typed identities.
        self.artifact_digest = model_weights_digest
        self.manifest_digest = model_manifest_digest
        self.weights_digest = model_weights_digest
        self.ssh_pid = ssh_pid
        self.runtime_attestation = runtime_attestation
        self.last_observation: OllamaNativeObservation | None = None
        self._cold_request_pending = False
        self._request_phase_uncertain = False

    @classmethod
    def verify_runtime(
        cls,
        *,
        base_url: str,
        expected_manifest_digest: str,
        expected_weights_digest: str,
        ssh_pid: int,
        timeout_seconds: float = 5.0,
    ) -> "VerifiedResearchGpuOllamaProvider":
        """Verify SSH process, live server, exact artifact, and unloaded model."""

        if (
            expected_manifest_digest != RESEARCH_GPU_EXPECTED_MANIFEST_DIGEST
            or not _DIGEST.fullmatch(expected_manifest_digest)
        ):
            raise ResearchGpuAdapterError("Expected Ollama manifest digest is invalid or unpinned")
        if (
            expected_weights_digest != RESEARCH_GPU_EXPECTED_WEIGHTS_DIGEST
            or not _DIGEST.fullmatch(expected_weights_digest)
        ):
            raise ResearchGpuAdapterError("Expected GGUF weights digest is invalid or unpinned")
        transport = verify_ssh_forwarding_process(ssh_pid, base_url)
        server_version = _get_json(base_url, "/api/version", timeout_seconds).get("version")
        if not isinstance(server_version, str) or not _OLLAMA_VERSION.fullmatch(server_version):
            raise ResearchGpuAdapterError("Ollama server version could not be verified")
        identity = _verified_model_identity(base_url, timeout_seconds)
        if (
            identity.manifest_digest != expected_manifest_digest
            or identity.weights_digest != expected_weights_digest
        ):
            raise ResearchGpuAdapterError("Ollama manifest/weights identity pair does not match the approved model")
        loaded_before = _loaded_model_names(base_url, timeout_seconds)
        unloaded = RESEARCH_GPU_REQUIRED_MODEL not in loaded_before
        if not unloaded:
            response = httpx.post(
                f"{base_url}/api/generate",
                json={"model": RESEARCH_GPU_REQUIRED_MODEL, "keep_alive": 0},
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            _ = response.json()
            unloaded = RESEARCH_GPU_REQUIRED_MODEL not in _loaded_model_names(base_url, timeout_seconds)
        if not unloaded:
            raise ResearchGpuAdapterError("Ollama model remains loaded after unload request")
        now = datetime.now(UTC).isoformat()
        attestation = OllamaRuntimeAttestation(
            server_version=server_version,
            model_name=RESEARCH_GPU_REQUIRED_MODEL,
            manifest_digest=identity.manifest_digest,
            weights_digest=identity.weights_digest,
            weights_layer_media_type=identity.weights_layer_media_type,
            quantization=identity.quantization,
            transport=transport,
            local_endpoint=base_url.rstrip("/"),
            verified_at=now,
            cold_model_absent_at=now,
            loaded_model_names_before_unload=loaded_before,
        )
        adapter = cls(
            base_url=base_url,
            model_manifest_digest=identity.manifest_digest,
            model_weights_digest=identity.weights_digest,
            ssh_pid=ssh_pid,
            runtime_attestation=attestation,
        )
        adapter._cold_request_pending = True
        return adapter

    def prepare_cold_start(self) -> OllamaRuntimeAttestation:
        """Recheck the tunnel/digest and ensure the target is unloaded now."""

        self._assert_tunnel_unchanged()
        server_version = _get_json(self.base_url, "/api/version", 5.0).get("version")
        identity = _verified_model_identity(self.base_url, 5.0)
        if (
            server_version != self.runtime_attestation.server_version
            or identity.manifest_digest != self.manifest_digest
            or identity.weights_digest != self.weights_digest
            or identity.quantization != RESEARCH_GPU_EXPECTED_QUANTIZATION
        ):
            raise ResearchGpuAdapterError("Ollama server or model authority changed before evaluation")
        loaded_before = _loaded_model_names(self.base_url, 5.0)
        if RESEARCH_GPU_REQUIRED_MODEL in loaded_before:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": RESEARCH_GPU_REQUIRED_MODEL, "keep_alive": 0},
                timeout=5.0,
            )
            response.raise_for_status()
            _ = response.json()
        if RESEARCH_GPU_REQUIRED_MODEL in _loaded_model_names(self.base_url, 5.0):
            raise ResearchGpuAdapterError("Ollama model is not cold at evaluation start")
        self.runtime_attestation = OllamaRuntimeAttestation(
            server_version=self.runtime_attestation.server_version,
            model_name=RESEARCH_GPU_REQUIRED_MODEL,
            manifest_digest=self.manifest_digest,
            weights_digest=self.weights_digest,
            weights_layer_media_type=RESEARCH_GPU_MODEL_LAYER_MEDIA_TYPE,
            quantization=RESEARCH_GPU_EXPECTED_QUANTIZATION,
            transport=self.runtime_attestation.transport,
            local_endpoint=self.base_url,
            verified_at=self.runtime_attestation.verified_at,
            cold_model_absent_at=datetime.now(UTC).isoformat(),
            loaded_model_names_before_unload=loaded_before,
        )
        self._cold_request_pending = True
        self._request_phase_uncertain = False
        self.last_observation = None
        return self.runtime_attestation

    def runtime_verification_is_current(self) -> bool:
        try:
            self._assert_tunnel_unchanged()
            server_version = _get_json(self.base_url, "/api/version", 5.0).get("version")
            identity = _verified_model_identity(self.base_url, 5.0)
        except (ResearchGpuAdapterError, httpx.HTTPError):
            return False
        return (
            server_version == self.runtime_attestation.server_version
            and identity.manifest_digest == self.manifest_digest
            and identity.weights_digest == self.weights_digest
            and identity.quantization == RESEARCH_GPU_EXPECTED_QUANTIZATION
            and self.runtime_attestation.manifest_digest == self.manifest_digest
            and self.runtime_attestation.weights_digest == self.weights_digest
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.last_observation = None
        if self._request_phase_uncertain:
            raise ResearchGpuAdapterError(
                "Ollama request phase is uncertain after an incomplete response; reverify cold start before retrying"
            )
        try:
            self._assert_tunnel_unchanged()
        except ResearchGpuAdapterError:
            raise ResearchGpuAdapterError("Verified SSH transport is no longer active")
        phase = "cold" if self._cold_request_pending else "warm"
        self._cold_request_pending = False
        # Once a request is sent, a timeout leaves model residency unknown: the
        # server may have loaded or completed inference after the client stopped
        # waiting. Do not label the next call warm without a fresh cold-start
        # verification.
        self._request_phase_uncertain = True
        payload = _ollama_generate_payload(self.base_url, self.model, request)
        if payload.get("model") != RESEARCH_GPU_REQUIRED_MODEL:
            raise ResearchGpuAdapterError("Ollama response model identity changed")
        response = _ollama_response_from_payload(payload, self.model)
        load = _native_duration(payload.get("load_duration"))
        total = _native_duration(payload.get("total_duration"))
        prompt_eval = _native_duration(payload.get("prompt_eval_duration"))
        eval_duration = _native_duration(payload.get("eval_duration"))
        metrics_valid = all(value is not None for value in (load, total, prompt_eval, eval_duration))
        self.last_observation = OllamaNativeObservation(
            phase=phase,
            observed_at=datetime.now(UTC).isoformat(),
            load_duration_ns=load,
            total_duration_ns=total,
            prompt_eval_duration_ns=prompt_eval,
            eval_duration_ns=eval_duration,
            cold_load_confirmed=phase != "cold" or (load is not None and load > 0),
            native_metrics_valid=metrics_valid,
        )
        self._request_phase_uncertain = False
        return response

    def _assert_tunnel_unchanged(self) -> None:
        current = verify_ssh_forwarding_process(self.ssh_pid, self.base_url)
        if current != self.runtime_attestation.transport:
            raise ResearchGpuAdapterError("SSH forwarding identity changed after runtime verification")

    def runtime_binding_payload(self) -> dict[str, object]:
        self._assert_tunnel_unchanged()
        return self.runtime_attestation.to_payload()


def _get_json(base_url: str, path: str, timeout_seconds: float) -> dict[str, object]:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}{path}", timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError:
        raise ResearchGpuAdapterError("Ollama runtime verification request failed") from None
    except ValueError:
        raise ResearchGpuAdapterError("Ollama runtime response was not valid JSON") from None
    if not isinstance(payload, dict):
        raise ResearchGpuAdapterError("Ollama runtime response must be a JSON object")
    return payload


def _post_json(
    base_url: str,
    path: str,
    request_payload: dict[str, object],
    timeout_seconds: float,
) -> dict[str, object]:
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}{path}",
            json=request_payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError:
        raise ResearchGpuAdapterError("Ollama runtime verification request failed") from None
    except ValueError:
        raise ResearchGpuAdapterError("Ollama runtime response was not valid JSON") from None
    if not isinstance(payload, dict):
        raise ResearchGpuAdapterError("Ollama runtime response must be a JSON object")
    return payload


def _parse_authoritative_manifest(
    manifest_bytes: bytes,
    *,
    expected_manifest_digest: str = RESEARCH_GPU_EXPECTED_MANIFEST_DIGEST,
    expected_weights_digest: str = RESEARCH_GPU_EXPECTED_WEIGHTS_DIGEST,
) -> OllamaModelIdentity:
    if not isinstance(manifest_bytes, bytes) or not manifest_bytes:
        raise ResearchGpuAdapterError("Authoritative Ollama registry manifest is unavailable")
    actual_manifest_digest = f"sha256:{hashlib.sha256(manifest_bytes).hexdigest()}"
    if actual_manifest_digest != expected_manifest_digest or not _DIGEST.fullmatch(actual_manifest_digest):
        raise ResearchGpuAdapterError("Authoritative Ollama manifest checksum does not match the pinned identity")
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ResearchGpuAdapterError("Authoritative Ollama manifest is not valid JSON") from None
    if (
        not isinstance(manifest, dict)
        or manifest.get("schemaVersion") != 2
        or manifest.get("mediaType") != "application/vnd.docker.distribution.manifest.v2+json"
    ):
        raise ResearchGpuAdapterError("Authoritative Ollama manifest schema is invalid")
    layers = manifest.get("layers")
    if not isinstance(layers, list):
        raise ResearchGpuAdapterError("Authoritative Ollama manifest layers are invalid")
    model_layers = [
        layer
        for layer in layers
        if isinstance(layer, dict) and layer.get("mediaType") == RESEARCH_GPU_MODEL_LAYER_MEDIA_TYPE
    ]
    if len(model_layers) != 1:
        raise ResearchGpuAdapterError("Authoritative Ollama manifest has a missing or ambiguous GGUF model layer")
    weights_digest = model_layers[0].get("digest")
    if not isinstance(weights_digest, str) or not _DIGEST.fullmatch(weights_digest):
        raise ResearchGpuAdapterError("Authoritative GGUF model-layer digest is absent or truncated")
    if weights_digest != expected_weights_digest:
        raise ResearchGpuAdapterError("Authoritative GGUF model-layer digest does not match the approved weights")
    return OllamaModelIdentity(
        manifest_digest=actual_manifest_digest,
        weights_digest=weights_digest,
        weights_layer_media_type=RESEARCH_GPU_MODEL_LAYER_MEDIA_TYPE,
        quantization=RESEARCH_GPU_EXPECTED_QUANTIZATION,
    )


def _authoritative_manifest_identity() -> OllamaModelIdentity:
    try:
        manifest_bytes = RESEARCH_GPU_MANIFEST_EVIDENCE_PATH.read_bytes()
    except OSError:
        raise ResearchGpuAdapterError("Pinned authoritative Ollama registry evidence is unavailable") from None
    return _parse_authoritative_manifest(manifest_bytes)


def _verified_model_identity(base_url: str, timeout_seconds: float) -> OllamaModelIdentity:
    authoritative = _authoritative_manifest_identity()
    payload = _get_json(base_url, "/api/tags", timeout_seconds)
    models = payload.get("models")
    if not isinstance(models, list):
        raise ResearchGpuAdapterError("Ollama model catalog is invalid")
    matching = [
        item
        for item in models
        if isinstance(item, dict)
        and item.get("name") == RESEARCH_GPU_REQUIRED_MODEL
    ]
    if len(matching) != 1:
        raise ResearchGpuAdapterError("Exact Qwen model is missing or ambiguous in Ollama catalog")
    digest = matching[0].get("digest")
    if isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest):
        digest = f"sha256:{digest}"
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise ResearchGpuAdapterError("Ollama manifest digest is absent, invalid, or truncated")
    if digest != authoritative.manifest_digest:
        raise ResearchGpuAdapterError("Ollama catalog manifest digest does not match authoritative registry evidence")

    shown = _post_json(
        base_url,
        "/api/show",
        {"model": RESEARCH_GPU_REQUIRED_MODEL},
        timeout_seconds,
    )
    details = shown.get("details")
    modelfile = shown.get("modelfile")
    if not isinstance(details, dict) or not isinstance(modelfile, str):
        raise ResearchGpuAdapterError("Ollama show response lacks model details or Modelfile evidence")
    shown_model = shown.get("model", shown.get("name"))
    if shown_model is not None and shown_model != RESEARCH_GPU_REQUIRED_MODEL:
        raise ResearchGpuAdapterError("Ollama show response model identity does not match the exact approved tag")
    if details.get("format") != "gguf" or details.get("family") != "qwen2":
        raise ResearchGpuAdapterError("Ollama show response does not identify the expected Qwen GGUF model")
    quantization = details.get("quantization_level")
    if quantization != RESEARCH_GPU_EXPECTED_QUANTIZATION:
        raise ResearchGpuAdapterError("Ollama model quantization does not match the approved Q4_K_M artifact")
    from_paths = re.findall(r"(?im)^FROM\s+(\S+)\s*$", modelfile)
    if len(from_paths) != 1:
        raise ResearchGpuAdapterError("Ollama Modelfile has a missing or ambiguous model blob reference")
    blob_path = PurePosixPath(from_paths[0])
    if (
        not blob_path.is_absolute()
        or len(blob_path.parts) < 4
        or blob_path.parts[-3:-1] != ("models", "blobs")
    ):
        raise ResearchGpuAdapterError("Ollama Modelfile does not reference a local model blob path")
    blob_name = blob_path.name
    blob_match = re.fullmatch(r"sha256-([0-9a-f]{64})", blob_name)
    if blob_match is None:
        raise ResearchGpuAdapterError("Ollama local model blob reference is absent, invalid, or truncated")
    local_weights_digest = f"sha256:{blob_match.group(1)}"
    if local_weights_digest != authoritative.weights_digest:
        raise ResearchGpuAdapterError("Ollama local model blob does not match the authoritative GGUF layer")
    _verify_local_model_blob(base_url, local_weights_digest, timeout_seconds)
    return OllamaModelIdentity(
        manifest_digest=digest,
        weights_digest=local_weights_digest,
        weights_layer_media_type=authoritative.weights_layer_media_type,
        quantization=quantization,
    )


def _verify_local_model_blob(base_url: str, weights_digest: str, timeout_seconds: float) -> None:
    """Use Ollama's read-only local blob-existence endpoint over the SSH tunnel."""

    try:
        response = httpx.head(
            f"{base_url.rstrip('/')}/api/blobs/{weights_digest}",
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        raise ResearchGpuAdapterError("Pinned Ollama model blob is not available on the local runtime") from None
    if response.status_code != 200:
        raise ResearchGpuAdapterError("Pinned Ollama model blob is not available on the local runtime")


def _loaded_model_names(base_url: str, timeout_seconds: float) -> tuple[str, ...]:
    payload = _get_json(base_url, "/api/ps", timeout_seconds)
    models = payload.get("models")
    if not isinstance(models, list):
        raise ResearchGpuAdapterError("Ollama loaded-model response is invalid")
    names: list[str] = []
    for item in models:
        if not isinstance(item, dict):
            raise ResearchGpuAdapterError("Ollama loaded-model item is invalid")
        name = item.get("name", item.get("model"))
        if not isinstance(name, str) or not name:
            raise ResearchGpuAdapterError("Ollama loaded-model identity is invalid")
        names.append(name)
    return tuple(sorted(names))


def _native_duration(value: object) -> int | None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > _MAX_NATIVE_DURATION_NS
    ):
        return None
    return value
