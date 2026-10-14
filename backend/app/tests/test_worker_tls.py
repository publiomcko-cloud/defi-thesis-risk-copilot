from __future__ import annotations

import hashlib
import hmac
import fcntl
import os
import shutil
import socket
import ssl
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.db.session import normalize_database_url
from app.jobs import worker_tls
from app.jobs.worker_tls import (
    CA_RELATIVE_PATH,
    WorkerTLSConfigurationError,
    _load_pinned_ca,
    _prepare_worker_environment,
)

EXPECTED_HOST = "aws-0-ca-central-1.pooler.supabase.com"
EXPECTED_PORT = 5432
EXPECTED_USER = "phase17_github_worker.jtgxtlbrisswtrezzxgu"
EXPECTED_DATABASE = "postgres"
EXPECTED_SSLMODE = "verify-full"
EXPECTED_DER_SHA256 = "807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa"
EXPECTED_FILE_SHA256 = "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
# Independently maintained from PostgreSQL 17's libpq environment-variable
# reference; do not derive this expected list from worker_tls.
POSTGRES_17_LIBPQ_ENVIRONMENT_VARIABLES = (
    "PGHOST", "PGHOSTADDR", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD",
    "PGPASSFILE", "PGREQUIREAUTH", "PGCHANNELBINDING", "PGSERVICE", "PGSERVICEFILE",
    "PGOPTIONS", "PGAPPNAME", "PGSSLMODE", "PGREQUIRESSL", "PGSSLCOMPRESSION",
    "PGSSLCERT", "PGSSLKEY", "PGSSLCERTMODE", "PGSSLROOTCERT", "PGSSLCRL",
    "PGSSLCRLDIR", "PGSSLSNI", "PGREQUIREPEER", "PGSSLMINPROTOCOLVERSION",
    "PGSSLMAXPROTOCOLVERSION", "PGGSSENCMODE", "PGKRBSRVNAME", "PGGSSLIB",
    "PGGSSDELEGATION", "PGCONNECT_TIMEOUT", "PGCLIENTENCODING", "PGTARGETSESSIONATTRS",
    "PGLOADBALANCEHOSTS", "PGDATESTYLE", "PGTZ", "PGGEQO", "PGSYSCONFDIR", "PGLOCALEDIR",
    "PGSSLNEGOTIATION",
)
APPROVED_TRANSPORT_ENVIRONMENT = {"PGSSLMODE", "PGGSSENCMODE", "PGSSLROOTCERT"}
SYNTHETIC_PASSWORD = "synthetic%40%3A%2F%25"
CANONICAL_URL = (
    f"postgresql://{EXPECTED_USER}:{SYNTHETIC_PASSWORD}@{EXPECTED_HOST}:{EXPECTED_PORT}/{EXPECTED_DATABASE}"
)


def _matches_synthetic_password(value: str | None) -> bool:
    return hmac.compare_digest(value or "", "synthetic@:/%")


def _configure_with_local_ca(url: str, certificate: Path, der_sha256: str, file_sha256: str) -> str:
    _load_pinned_ca(certificate, der_sha256, file_sha256)
    return worker_tls._normalize_database_url(url, str(certificate.resolve()))


def _make_local_certificate(directory: Path, name: str = "local-ca") -> tuple[Path, Path, str, str]:
    certificate = directory / f"{name}.pem"
    private_key = directory / f"{name}.key"
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(private_key), "-out", str(certificate), "-days", "1",
            "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost",
            "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,digitalSignature,keyCertSign,cRLSign",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    der = ssl.PEM_cert_to_DER_cert(certificate.read_text(encoding="ascii"))
    return (
        certificate,
        private_key,
        hashlib.sha256(der).hexdigest(),
        hashlib.sha256(certificate.read_bytes()).hexdigest(),
    )


def _local_tls_handshake(certificate: Path, private_key: Path, hostname: str) -> None:
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.minimum_version = ssl.TLSVersion.TLSv1_2
    server_context.load_cert_chain(str(certificate), str(private_key))
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    server_errors: list[BaseException] = []

    def serve_once() -> None:
        try:
            connection, _ = listener.accept()
            with connection, server_context.wrap_socket(connection, server_side=True):
                pass
        except BaseException as exc:  # surfaced below; test server runs in a thread
            server_errors.append(exc)
        finally:
            listener.close()

    server = threading.Thread(target=serve_once, daemon=True)
    server.start()
    client_context = ssl.create_default_context(cafile=str(certificate))
    client_context.minimum_version = ssl.TLSVersion.TLSv1_2
    client_error: ssl.SSLError | None = None
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=3) as raw:
            with client_context.wrap_socket(raw, server_hostname=hostname):
                pass
    except ssl.SSLError as exc:
        client_error = exc
    server.join(timeout=3)
    assert not server.is_alive()
    if client_error is not None:
        raise client_error
    assert not server_errors


def test_checked_in_supabase_root_matches_pinned_fingerprint() -> None:
    certificate = Path(__file__).parents[2] / CA_RELATIVE_PATH.relative_to("backend")
    assert hashlib.sha256(certificate.read_bytes()).hexdigest() == EXPECTED_FILE_SHA256
    context = _load_pinned_ca(certificate, EXPECTED_DER_SHA256, EXPECTED_FILE_SHA256)
    assert worker_tls.SUPABASE_ROOT_SHA256 == EXPECTED_DER_SHA256
    assert worker_tls.SUPABASE_ROOT_FILE_SHA256 == EXPECTED_FILE_SHA256
    assert set(worker_tls._LIBPQ_ENVIRONMENT_VARIABLES) == set(POSTGRES_17_LIBPQ_ENVIRONMENT_VARIABLES)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert len(context.get_ca_certs()) == 1


def test_missing_ca_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(WorkerTLSConfigurationError):
        _load_pinned_ca(tmp_path / "missing.pem", "0" * 64, "1" * 64)


def test_malformed_ca_fails_closed(tmp_path: Path) -> None:
    malformed = tmp_path / "bad.pem"
    malformed.write_text("not a certificate", encoding="ascii")
    with pytest.raises(WorkerTLSConfigurationError):
        _load_pinned_ca(malformed, "0" * 64, "1" * 64)


def test_incorrect_ca_fingerprint_fails_closed(tmp_path: Path) -> None:
    certificate, _, _, file_fingerprint = _make_local_certificate(tmp_path)
    with pytest.raises(WorkerTLSConfigurationError):
        _load_pinned_ca(certificate, "0" * 64, file_fingerprint)


def test_approved_root_plus_rogue_root_bundle_is_rejected(tmp_path: Path) -> None:
    approved = Path(__file__).parents[2] / CA_RELATIVE_PATH.relative_to("backend")
    rogue, _, _, _ = _make_local_certificate(tmp_path, "rogue-root")
    bundle = tmp_path / "bundle.pem"
    bundle.write_bytes(approved.read_bytes() + rogue.read_bytes())
    with pytest.raises(WorkerTLSConfigurationError):
        _load_pinned_ca(bundle)


def test_additional_certificate_and_trailing_non_pem_data_are_rejected(tmp_path: Path) -> None:
    approved = Path(__file__).parents[2] / CA_RELATIVE_PATH.relative_to("backend")
    rogue, _, _, _ = _make_local_certificate(tmp_path, "additional-root")
    additional = tmp_path / "additional.pem"
    additional.write_bytes(approved.read_bytes() + rogue.read_bytes())
    trailing = tmp_path / "trailing.pem"
    trailing.write_bytes(approved.read_bytes() + b"unexpected trailing data\n")
    with pytest.raises(WorkerTLSConfigurationError):
        _load_pinned_ca(additional)
    with pytest.raises(WorkerTLSConfigurationError):
        _load_pinned_ca(trailing)


def test_modified_or_wrong_certificate_is_rejected(tmp_path: Path) -> None:
    approved = Path(__file__).parents[2] / CA_RELATIVE_PATH.relative_to("backend")
    modified = tmp_path / "modified.pem"
    modified_bytes = bytearray(approved.read_bytes())
    base64_start = modified_bytes.index(b"-----BEGIN CERTIFICATE-----") + len(b"-----BEGIN CERTIFICATE-----")
    while modified_bytes[base64_start] in b"\r\n":
        base64_start += 1
    modified_bytes[base64_start] = ord("A") if modified_bytes[base64_start] != ord("A") else ord("B")
    modified.write_bytes(modified_bytes)
    wrong, _, _, _ = _make_local_certificate(tmp_path, "wrong-root")
    with pytest.raises(WorkerTLSConfigurationError):
        _load_pinned_ca(modified)
    with pytest.raises(WorkerTLSConfigurationError):
        _load_pinned_ca(wrong)


def test_symlink_redirected_trust_path_is_rejected(tmp_path: Path) -> None:
    target, _, _, _ = _make_local_certificate(tmp_path, "redirect-target")
    redirected = tmp_path / "redirected.pem"
    redirected.symlink_to(target)
    with pytest.raises(WorkerTLSConfigurationError):
        _load_pinned_ca(redirected)


def test_wrong_hostname_is_rejected_by_tls_verification(tmp_path: Path) -> None:
    if shutil.which("openssl") is None:
        pytest.skip("OpenSSL is required to generate the isolated test certificate")
    certificate, private_key, _, _ = _make_local_certificate(tmp_path)
    with pytest.raises(ssl.SSLCertVerificationError):
        _local_tls_handshake(certificate, private_key, "wrong.example.invalid")


def test_valid_canonical_url_and_effective_psycopg_parameters(tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    configured = _configure_with_local_ca(CANONICAL_URL, certificate, fingerprint, file_fingerprint)

    # Independently check libpq's parsed result; the helper itself does not
    # supply expected values to this assertion.
    effective = conninfo_to_dict(configured.replace("postgresql+psycopg://", "postgresql://", 1))
    assert effective.get("host") == EXPECTED_HOST
    assert effective.get("port") == str(EXPECTED_PORT)
    assert effective.get("user") == EXPECTED_USER
    assert effective.get("dbname") == EXPECTED_DATABASE
    assert effective.get("sslmode") == EXPECTED_SSLMODE
    assert effective.get("gssencmode") == "disable"
    assert effective.get("sslrootcert") == str(certificate.resolve())
    assert _matches_synthetic_password(effective.get("password"))

    # Exercise the same normalization function used by the application and
    # SQLAlchemy's Psycopg dialect, without opening a connection.
    application_url = normalize_database_url(configured)
    assert application_url.startswith("postgresql+psycopg://")
    sqlalchemy_url = make_url(application_url)
    assert sqlalchemy_url.username == EXPECTED_USER
    assert _matches_synthetic_password(sqlalchemy_url.password)
    engine = create_engine(sqlalchemy_url)
    _, connect_parameters = engine.dialect.create_connect_args(engine.url)
    assert connect_parameters.get("host") == EXPECTED_HOST
    assert connect_parameters.get("port") == EXPECTED_PORT
    assert connect_parameters.get("user") == EXPECTED_USER
    assert connect_parameters.get("dbname") == EXPECTED_DATABASE
    assert _matches_synthetic_password(connect_parameters.get("password"))
    assert connect_parameters.get("sslmode") == EXPECTED_SSLMODE
    assert connect_parameters.get("gssencmode") == "disable"
    assert connect_parameters.get("sslrootcert") == str(certificate.resolve())
    engine.dispose()


def test_wrong_production_endpoint_constant_rejects_independently_expected_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    monkeypatch.setattr(worker_tls, "EXPECTED_HOST", "attacker.example.invalid")
    with pytest.raises(WorkerTLSConfigurationError):
        _configure_with_local_ca(CANONICAL_URL, certificate, fingerprint, file_fingerprint)


def test_worker_environment_is_sanitized_and_ca_descriptor_is_sealed(tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    hostile = {name: "attacker-controlled" for name in POSTGRES_17_LIBPQ_ENVIRONMENT_VARIABLES}
    hostile["DATABASE_URL"] = CANONICAL_URL
    fd, environment = _prepare_worker_environment(
        CANONICAL_URL,
        certificate,
        hostile,
        expected_sha256=fingerprint,
        expected_file_sha256=file_fingerprint,
    )
    try:
        assert all(
            name not in environment
            for name in POSTGRES_17_LIBPQ_ENVIRONMENT_VARIABLES
            if name not in APPROVED_TRANSPORT_ENVIRONMENT
        )
        assert environment.get("PGSSLMODE") == EXPECTED_SSLMODE
        assert environment.get("PGGSSENCMODE") == "disable"
        effective = conninfo_to_dict(environment["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1))
        assert effective.get("host") == EXPECTED_HOST
        assert effective.get("port") == str(EXPECTED_PORT)
        assert effective.get("user") == EXPECTED_USER
        assert effective.get("dbname") == EXPECTED_DATABASE
        assert effective.get("sslmode") == EXPECTED_SSLMODE
        assert effective.get("gssencmode") == "disable"
        assert effective.get("sslrootcert") == f"/proc/self/fd/{fd}"
        assert os.get_inheritable(fd)
        seals = fcntl.fcntl(fd, fcntl.F_GET_SEALS)
        required_seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
        assert seals & required_seals == required_seals
        assert os.read(fd, 8).startswith(b"-----BEG")

        # Exercise a real process exec boundary without contacting PostgreSQL.
        # close_fds=False proves the sealed descriptor is inherited because the
        # production launcher marks it inheritable before os.execvpe.
        child_check = (
            "import os; from pathlib import Path; from psycopg.conninfo import conninfo_to_dict; "
            "url=os.environ['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://', 1); "
            "params=conninfo_to_dict(url); "
            "assert os.environ['PGSSLMODE']=='verify-full'; "
            "assert os.environ['PGGSSENCMODE']=='disable'; "
            "assert params['sslmode']=='verify-full' and params['gssencmode']=='disable'; "
            "assert Path(os.environ['PGSSLROOTCERT']).read_bytes().startswith(b'-----BEGIN CERTIFICATE-----'); "
            "print('verified')"
        )
        child = subprocess.run(
            [sys.executable, "-c", child_check],
            env=environment,
            close_fds=False,
            capture_output=True,
            text=True,
            check=False,
        )
        assert child.returncode == 0
        assert child.stdout.strip() == "verified"
        assert child.stderr == ""
    finally:
        os.close(fd)


@pytest.mark.parametrize("hostile_mode", ["require", "prefer"])
def test_hostile_inherited_gss_mode_cannot_enable_gss_encryption(
    hostile_mode: str, tmp_path: Path
) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    hostile_environment = {
        "DATABASE_URL": CANONICAL_URL,
        "PGGSSENCMODE": hostile_mode,
        "PGSSLMODE": "disable",
        "PGSSLROOTCERT": "/tmp/untrusted-root.pem",
        "PGHOST": "hostile.example.invalid",
    }
    fd, environment = _prepare_worker_environment(
        CANONICAL_URL,
        certificate,
        hostile_environment,
        expected_sha256=fingerprint,
        expected_file_sha256=file_fingerprint,
    )
    try:
        effective = conninfo_to_dict(environment["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1))
        assert environment.get("PGGSSENCMODE") == "disable"
        assert environment.get("PGSSLMODE") == EXPECTED_SSLMODE
        assert environment.get("PGHOST") is None
        assert effective.get("gssencmode") == "disable"
        assert effective.get("sslmode") == EXPECTED_SSLMODE
        assert effective.get("host") == EXPECTED_HOST
        assert effective.get("sslrootcert") == f"/proc/self/fd/{fd}"
    finally:
        os.close(fd)


def test_gss_query_is_canonicalized_and_duplicates_are_rejected(tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    configured = _configure_with_local_ca(
        CANONICAL_URL + "?gssencmode=require",
        certificate,
        fingerprint,
        file_fingerprint,
    )
    effective = conninfo_to_dict(configured.replace("postgresql+psycopg://", "postgresql://", 1))
    assert effective.get("gssencmode") == "disable"
    assert effective.get("sslmode") == EXPECTED_SSLMODE
    with pytest.raises(WorkerTLSConfigurationError):
        _configure_with_local_ca(
            CANONICAL_URL + "?gssencmode=prefer&gssencmode=disable",
            certificate,
            fingerprint,
            file_fingerprint,
        )
    with pytest.raises(WorkerTLSConfigurationError):
        _configure_with_local_ca(
            CANONICAL_URL + "?gssencmode=allow",
            certificate,
            fingerprint,
            file_fingerprint,
        )


def test_validated_trust_bytes_survive_original_path_replacement(tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    fd, environment = _prepare_worker_environment(
        CANONICAL_URL,
        certificate,
        {"DATABASE_URL": CANONICAL_URL},
        expected_sha256=fingerprint,
        expected_file_sha256=file_fingerprint,
    )
    try:
        pinned_bytes = os.pread(fd, 65536, 0)
        certificate.write_bytes(b"replaced after verification")
        assert os.pread(fd, 65536, 0) == pinned_bytes
        assert environment["PGSSLROOTCERT"] == f"/proc/self/fd/{fd}"
    finally:
        os.close(fd)


def test_workflow_secrets_are_limited_to_validated_execution_step() -> None:
    workflow = Path(__file__).parents[3] / ".github/workflows/phase17-scheduled-worker.yml"
    source = workflow.read_text(encoding="utf-8")
    checkout = source.index("- name: Checkout default-branch worker code")
    setup = source.index("- name: Set up Python")
    install = source.index("- name: Install worker dependencies")
    execute = source.index("- name: Validate PostgreSQL TLS and process one durable job")
    assert checkout < setup < install < execute
    assert source.index("run: pip install -r requirements.txt") < execute
    assert source.count("secrets.") == 3
    assert source.index("secrets.WORKER_DATABASE_URL") > execute
    assert source.index("secrets.WORKER_CREDENTIAL") > execute
    assert source.index("secrets.WORKER_CONTROL_PLANE_URL") > execute
    assert "GITHUB_ENV" not in source
    assert "GITHUB_OUTPUT" not in source
    assert source.count("python -m app.jobs.worker_tls") == 1
    assert "python -m app.jobs.worker_runner --once" not in source
    bootstrap = Path(__file__).parents[1] / "jobs/worker_tls.py"
    bootstrap_source = bootstrap.read_text(encoding="utf-8")
    assert "GITHUB_ENV" not in bootstrap_source
    assert "GITHUB_OUTPUT" not in bootstrap_source


def test_successful_preflight_execs_only_the_worker_with_validated_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = tmp_path / "workspace"
    ca_path = workspace / CA_RELATIVE_PATH
    ca_path.parent.mkdir(parents=True)
    approved_ca = Path(__file__).parents[2] / CA_RELATIVE_PATH.relative_to("backend")
    ca_path.write_bytes(approved_ca.read_bytes())
    monkeypatch.setenv("GITHUB_WORKSPACE", str(workspace))
    monkeypatch.setenv("DATABASE_URL", CANONICAL_URL)
    monkeypatch.setenv("WORKER_CONTROL_PLANE_URL", "https://control.invalid")
    monkeypatch.setenv("WORKER_CREDENTIAL", "synthetic-worker-token")
    captured: dict[str, object] = {}

    class ExecIntercept(Exception):
        pass

    def intercept(executable: str, args: list[str], environment: dict[str, str]) -> None:
        captured["args"] = args
        captured["environment"] = environment
        raise ExecIntercept

    monkeypatch.setattr(os, "execvpe", intercept)
    with pytest.raises(SystemExit) as exit_error:
        worker_tls.run_worker()
    output = capsys.readouterr()
    assert exit_error.value.code == 1
    assert captured["args"] == [sys.executable, "-m", "app.jobs.worker_runner", "--once"]
    worker_environment = captured["environment"]
    assert isinstance(worker_environment, dict)
    effective = conninfo_to_dict(worker_environment["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1))
    assert effective.get("host") == EXPECTED_HOST
    assert effective.get("sslmode") == EXPECTED_SSLMODE
    assert worker_environment.get("WORKER_CONTROL_PLANE_URL") == "https://control.invalid"
    assert worker_environment.get("WORKER_CREDENTIAL") == "synthetic-worker-token"
    assert "synthetic-worker-token" not in output.out + output.err


def test_preflight_failure_never_executes_worker_and_error_is_generic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = tmp_path / "workspace"
    ca_path = workspace / CA_RELATIVE_PATH
    ca_path.parent.mkdir(parents=True)
    approved_ca = Path(__file__).parents[2] / CA_RELATIVE_PATH.relative_to("backend")
    ca_path.write_bytes(approved_ca.read_bytes())
    monkeypatch.setenv("GITHUB_WORKSPACE", str(workspace))
    monkeypatch.setenv("DATABASE_URL", CANONICAL_URL + "?host=hostile.example.invalid")
    executed: list[bool] = []
    monkeypatch.setattr(os, "execvpe", lambda *args, **kwargs: executed.append(True))
    with pytest.raises(SystemExit) as exit_error:
        worker_tls.run_worker()
    captured = capsys.readouterr()
    assert exit_error.value.code == 1
    assert not executed
    assert "worker was not started" in captured.err
    assert SYNTHETIC_PASSWORD not in captured.out + captured.err


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(CANONICAL_URL.replace(EXPECTED_HOST, "other.example.invalid"), id="wrong-host"),
        pytest.param(CANONICAL_URL.replace(EXPECTED_USER, "wrong_role"), id="wrong-user"),
        pytest.param(CANONICAL_URL.replace(":5432/", ":6543/"), id="wrong-port"),
        pytest.param(CANONICAL_URL.replace("/postgres", "/otherdb"), id="wrong-database"),
        pytest.param(CANONICAL_URL.replace(f":{SYNTHETIC_PASSWORD}", ""), id="missing-password"),
        pytest.param(CANONICAL_URL.replace(f":{SYNTHETIC_PASSWORD}", ":"), id="empty-password"),
        pytest.param("postgres://" + CANONICAL_URL.split("://", 1)[1], id="unexpected-scheme"),
        pytest.param(CANONICAL_URL.replace(":5432/", ":badport/"), id="invalid-port"),
        pytest.param(CANONICAL_URL.replace("postgresql://", "postgresql://other@", 1), id="ambiguous-authority"),
        pytest.param(CANONICAL_URL + "#fragment", id="fragment"),
        pytest.param(CANONICAL_URL.replace("/postgres", "/%70ostgres"), id="noncanonical-database-path"),
    ],
)
def test_unapproved_endpoint_or_malformed_url_rejected(url: str, tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    with pytest.raises(WorkerTLSConfigurationError):
        _configure_with_local_ca(url, certificate, fingerprint, file_fingerprint)


@pytest.mark.parametrize("escape", ["%ZZ", "%2", "%", "%G0"])
def test_invalid_percent_escapes_rejected(escape: str, tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    url = CANONICAL_URL.replace("synthetic", f"synthetic{escape}")
    with pytest.raises(WorkerTLSConfigurationError):
        _configure_with_local_ca(url, certificate, fingerprint, file_fingerprint)


@pytest.mark.parametrize(
    "parameter",
    [
        "host=other.example.invalid", "hostaddr=127.0.0.1", "user=other", "port=6543",
        "dbname=other", "password=other", "service=other", "servicefile=/tmp/service",
        "passfile=/tmp/pass", "options=-csearch_path=other", "target_session_attrs=any",
        "unknown_option=x",
    ],
)
def test_unapproved_libpq_query_parameters_rejected(parameter: str, tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    with pytest.raises(WorkerTLSConfigurationError):
        _configure_with_local_ca(CANONICAL_URL + "?" + parameter, certificate, fingerprint, file_fingerprint)


@pytest.mark.parametrize(
    "query",
    [
        "sslmode=require&sslmode=verify-full",
        "sslrootcert=/tmp/attacker.pem&sslrootcert=/tmp/other.pem",
        "SSLmode=prefer&sslmode=require",
    ],
)
def test_duplicate_or_conflicting_tls_parameters_are_normalized_or_rejected(query: str, tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    with pytest.raises(WorkerTLSConfigurationError):
        _configure_with_local_ca(CANONICAL_URL + "?" + query, certificate, fingerprint, file_fingerprint)


def test_single_weaker_tls_values_are_replaced_with_strict_tls(tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    configured = _configure_with_local_ca(
        CANONICAL_URL + "?sslmode=require&sslrootcert=%2Fold%2Fca.pem&application_name=worker",
        certificate,
        fingerprint,
        file_fingerprint,
    )
    query = parse_qs(urlsplit(configured).query)
    assert query.get("sslmode") == ["verify-full"]
    assert query.get("sslrootcert") == [str(certificate.resolve())]
    assert query.get("application_name") == ["worker"]


def test_single_disable_tls_value_is_replaced_with_strict_tls(tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    configured = _configure_with_local_ca(
        CANONICAL_URL + "?sslmode=disable", certificate, fingerprint, file_fingerprint
    )
    query = parse_qs(urlsplit(configured).query)
    assert query.get("sslmode") == ["verify-full"]
    assert query.get("sslrootcert") == [str(certificate.resolve())]


def test_duplicate_query_parameters_rejected(tmp_path: Path) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    with pytest.raises(WorkerTLSConfigurationError):
        _configure_with_local_ca(CANONICAL_URL + "?application_name=a&application_name=b", certificate, fingerprint, file_fingerprint)


def test_safe_errors_do_not_disclose_url_or_secret(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    certificate, _, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    secret_marker = "do-not-disclose-synthetic-secret"
    unsafe_url = CANONICAL_URL.replace(SYNTHETIC_PASSWORD, secret_marker) + "?host=attacker"
    with pytest.raises(WorkerTLSConfigurationError) as error:
        _configure_with_local_ca(unsafe_url, certificate, fingerprint, file_fingerprint)
    captured = capsys.readouterr()
    assert secret_marker not in str(error.value)
    assert secret_marker not in captured.out
    assert secret_marker not in captured.err


def test_local_tls_and_database_url_use_verify_full(tmp_path: Path) -> None:
    if shutil.which("openssl") is None:
        pytest.skip("OpenSSL is required to generate the isolated test certificate")
    certificate, private_key, fingerprint, file_fingerprint = _make_local_certificate(tmp_path)
    context = _load_pinned_ca(certificate, fingerprint, file_fingerprint)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    _local_tls_handshake(certificate, private_key, "localhost")
    configured = _configure_with_local_ca(CANONICAL_URL, certificate, fingerprint, file_fingerprint)
    effective = conninfo_to_dict(configured.replace("postgresql+psycopg://", "postgresql://", 1))
    assert effective.get("sslmode") == EXPECTED_SSLMODE
    assert effective.get("sslrootcert") == str(certificate.resolve())
