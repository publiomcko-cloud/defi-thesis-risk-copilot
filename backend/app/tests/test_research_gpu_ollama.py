from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.llm.base import LLMRequest
from app.llm.provenance import provider_identity, provider_is_eligible_for_scope
from app.llm import research_gpu_ollama as adapter_module
from app.llm.research_gpu_ollama import (
    ResearchGpuAdapterError,
    SshForwardingEvidence,
    VerifiedResearchGpuOllamaProvider,
    verify_ssh_forwarding_process,
)


MODEL = "qwen2.5:7b-instruct-q4_K_M"
DIGEST = "sha256:" + "a" * 64
URL = "http://127.0.0.1:11435"
PID = 4242


class Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self.payload


def _proc_fixture(tmp_path: Path, *, strict: bool = True, executable: str = "/usr/bin/ssh") -> Path:
    process_dir = tmp_path / str(PID)
    process_dir.mkdir(parents=True)
    (process_dir / "stat").write_text(f"{PID} (ssh) S 1 0 0\n")
    (process_dir / "exe").symlink_to(executable)
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("[203.0.113.10]:2222 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFAKE\n")
    strict_value = "yes" if strict else "no"
    argv = [
        "/usr/bin/ssh",
        "-F", "/dev/null",
        "-N", "-T",
        "-o", "BatchMode=yes",
        "-o", "ExitOnForwardFailure=yes",
        "-o", f"StrictHostKeyChecking={strict_value}",
        "-o", f"UserKnownHostsFile={known_hosts}",
        "-L", "127.0.0.1:11435:127.0.0.1:11434",
        "-p", "2222",
        "root@203.0.113.10",
    ]
    (process_dir / "cmdline").write_bytes(b"\0".join(value.encode() for value in argv) + b"\0")
    return tmp_path


def test_ssh_tunnel_verification_checks_live_process_forward_and_host_key_policy(tmp_path: Path) -> None:
    proc_root = _proc_fixture(tmp_path)
    proof = verify_ssh_forwarding_process(PID, URL, proc_root=proc_root)
    assert proof.ssh_target == "root@203.0.113.10"
    assert proof.ssh_port == 2222
    assert proof.local_port == 11435
    assert len(proof.known_hosts_sha256) == 64
    assert len(proof.ssh_command_sha256) == 64

    bad_proc = tmp_path / "bad"
    _proc_fixture(bad_proc, strict=False)
    with pytest.raises(ResearchGpuAdapterError, match="strict host-key"):
        verify_ssh_forwarding_process(PID, URL, proc_root=bad_proc)

    with pytest.raises(ResearchGpuAdapterError, match="loopback URL"):
        verify_ssh_forwarding_process(PID, "https://gpu.example:11435", proc_root=proc_root)


def _provider(monkeypatch, *, loaded: list[str] | None = None) -> VerifiedResearchGpuOllamaProvider:
    current_loaded = loaded if loaded is not None else []
    proof = SshForwardingEvidence(
        ssh_pid=PID,
        ssh_target="root@203.0.113.10",
        ssh_port=2222,
        local_port=11435,
        known_hosts_sha256="b" * 64,
        ssh_command_sha256="c" * 64,
    )
    monkeypatch.setattr(adapter_module, "verify_ssh_forwarding_process", lambda *_args, **_kwargs: proof)

    def get(url: str, *, timeout: float) -> Response:
        assert timeout > 0
        if url.endswith("/api/version"):
            return Response({"version": "0.13.2"})
        if url.endswith("/api/tags"):
            return Response({"models": [{"name": MODEL, "digest": "a" * 64}]})
        if url.endswith("/api/ps"):
            return Response({"models": [{"name": name} for name in current_loaded]})
        raise AssertionError(url)

    monkeypatch.setattr(adapter_module.httpx, "get", get)
    return VerifiedResearchGpuOllamaProvider.verify_runtime(
        base_url=URL,
        expected_model_digest=DIGEST,
        ssh_pid=PID,
    )


def test_runtime_verification_reads_digest_and_unloads_loaded_model(monkeypatch) -> None:
    loaded = [MODEL]
    unload_requests: list[tuple[str, dict[str, object]]] = []

    def post(url: str, *, json: dict[str, object], timeout: float) -> Response:
        assert timeout > 0
        unload_requests.append((url, json))
        loaded.clear()
        return Response({"done": True})

    monkeypatch.setattr(adapter_module.httpx, "post", post)
    provider = _provider(monkeypatch, loaded=loaded)
    assert provider.artifact_digest == DIGEST
    assert provider.runtime_attestation.loaded_model_names_before_unload == (MODEL,)
    assert loaded == []
    assert unload_requests == [(f"{URL}/api/generate", {"model": MODEL, "keep_alive": 0})]
    cold_evidence = provider.prepare_cold_start()
    assert cold_evidence.cold_model_absent_at
    assert loaded == []


def test_runtime_digest_mismatch_and_spoofed_metadata_are_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        adapter_module,
        "verify_ssh_forwarding_process",
        lambda *_args, **_kwargs: SshForwardingEvidence(PID, "root@203.0.113.10", 2222, 11435, "b" * 64, "c" * 64),
    )
    monkeypatch.setattr(
        adapter_module.httpx,
        "get",
        lambda url, *, timeout: Response(
            {"version": "0.13.2"} if url.endswith("/api/version") else
            {"models": [{"name": MODEL, "digest": "f" * 64}]} if url.endswith("/api/tags") else
            {"models": []}
        ),
    )
    with pytest.raises(ResearchGpuAdapterError, match="does not match"):
        VerifiedResearchGpuOllamaProvider.verify_runtime(
            base_url=URL,
            expected_model_digest=DIGEST,
            ssh_pid=PID,
        )

    class SpoofedProvider:
        name = "ollama"
        model = MODEL
        privacy_classification = "public_only"
        artifact_digest = DIGEST
        base_url = URL

    from app.llm.research_gpu_policy import research_gpu_provider_is_allowed

    assert not research_gpu_provider_is_allowed(SpoofedProvider(), DIGEST)


def test_genuine_generate_request_preserves_timeout_json_usage_and_native_timings(monkeypatch) -> None:
    provider = _provider(monkeypatch)
    provider.prepare_cold_start()
    requests: list[tuple[str, dict[str, object], float]] = []

    def post(url: str, *, json: dict[str, object], timeout: float) -> Response:
        requests.append((url, json, timeout))
        return Response({
            "model": MODEL,
            "response": '{"sections":{"Overview":"Synthetic result"}}',
            "prompt_eval_count": 31,
            "eval_count": 12,
            "load_duration": 900_000_000,
            "total_duration": 2_500_000_000,
            "prompt_eval_duration": 700_000_000,
            "eval_duration": 900_000_000,
        })

    monkeypatch.setattr(adapter_module.httpx, "post", post)
    result = provider.generate(LLMRequest("synthetic public fixture", 45, 222, "bounded system"))
    assert requests == [(
        f"{URL}/api/generate",
        {
            "model": MODEL,
            "prompt": "synthetic public fixture",
            "system": "bounded system",
            "stream": False,
            "format": "json",
            "options": {"num_predict": 222},
        },
        45,
    )]
    assert result.input_tokens == 31 and result.output_tokens == 12
    assert result.usage_invalid_fields == ()
    assert provider.last_observation is not None
    assert provider.last_observation.phase == "cold"
    assert provider.last_observation.cold_load_confirmed is True
    assert provider.last_observation.load_duration_ns == 900_000_000
    assert provider.last_observation.native_metrics_valid is True
    assert not provider_is_eligible_for_scope(provider_identity(provider), "private")


@pytest.mark.parametrize(
    ("payload", "invalid_fields"),
    [
        ({"model": MODEL, "response": "{}", "eval_count": 3}, ("prompt_eval_count",)),
        ({"model": MODEL, "response": "{}", "prompt_eval_count": True, "eval_count": -1}, ("prompt_eval_count", "eval_count")),
    ],
)
def test_missing_or_invalid_usage_is_not_filled_with_favorable_defaults(monkeypatch, payload, invalid_fields) -> None:
    provider = _provider(monkeypatch)
    provider.prepare_cold_start()
    invalid = {
        **payload,
        "load_duration": 0,
        "total_duration": 100,
        "prompt_eval_duration": 10,
        "eval_duration": 20,
    }
    monkeypatch.setattr(adapter_module.httpx, "post", lambda *_args, **_kwargs: Response(invalid))
    response = provider.generate(LLMRequest("synthetic", 45))
    assert response.input_tokens is None or "prompt_eval_count" in invalid_fields
    assert response.usage_invalid_fields == invalid_fields
    assert provider.last_observation is not None
    assert provider.last_observation.cold_load_confirmed is False


@pytest.mark.parametrize("error", [httpx.ConnectError("offline"), httpx.ReadTimeout("timeout")])
def test_adapter_surfaces_transport_errors_and_timeouts(monkeypatch, error) -> None:
    provider = _provider(monkeypatch)
    provider.prepare_cold_start()

    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(adapter_module.httpx, "post", fail)
    with pytest.raises(type(error)):
        provider.generate(LLMRequest("synthetic", 45))
    assert provider.last_observation is None
