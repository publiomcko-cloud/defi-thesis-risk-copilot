"""Validate pinned PostgreSQL TLS configuration, then exec the worker in-place."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import os
import re
import stat
import ssl
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from psycopg.conninfo import conninfo_to_dict
from sqlalchemy.engine import make_url

SUPABASE_ROOT_SHA256 = "807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa"
SUPABASE_ROOT_FILE_SHA256 = "700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7"
CA_RELATIVE_PATH = Path("backend/certs/supabase-root-2021-ca.crt")
EXPECTED_HOST = "aws-0-ca-central-1.pooler.supabase.com"
EXPECTED_PORT = 5432
EXPECTED_USER = "phase17_github_worker.jtgxtlbrisswtrezzxgu"
EXPECTED_DATABASE = "postgres"
_ALLOWED_QUERY_KEYS = {"application_name", "connect_timeout", "gssencmode", "sslmode", "sslrootcert"}
# PostgreSQL 17 libpq envars from its documented environment-variable list.
# The worker restores only the three strict transport values below.
_LIBPQ_ENVIRONMENT_VARIABLES = (
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
_BAD_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_PEM_CERT_BEGIN = b"-----BEGIN CERTIFICATE-----"
_PEM_CERT_END = b"-----END CERTIFICATE-----"


class WorkerTLSConfigurationError(ValueError):
    """Raised when the worker's PostgreSQL TLS configuration is unsafe."""


def _open_absolute_nofollow(path: Path) -> int:
    """Open an absolute regular file without following symlinks in any component."""
    if not path.is_absolute() or ".." in path.parts:
        raise WorkerTLSConfigurationError("CA path is not approved")
    parts = path.parts[1:]
    if not parts:
        raise WorkerTLSConfigurationError("CA file is missing or malformed")
    directory_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in parts[:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise WorkerTLSConfigurationError("CA file is missing or malformed")
    return fd


def _read_verified_ca_fd(
    fd: int,
    *,
    expected_der_sha256: str,
    expected_file_sha256: str,
) -> bytes:
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 65536:
            raise WorkerTLSConfigurationError("CA file is missing or malformed")
        os.lseek(fd, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = 65537
        while remaining:
            chunk = os.read(fd, min(remaining, 8192))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        pem = b"".join(chunks)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size) != (after.st_dev, after.st_ino, after.st_size):
            raise WorkerTLSConfigurationError("CA file changed during validation")
        if len(pem) != after.st_size or len(pem) > 65536:
            raise WorkerTLSConfigurationError("CA file is missing or malformed")
        if not hmac.compare_digest(hashlib.sha256(pem).hexdigest(), expected_file_sha256.lower()):
            raise WorkerTLSConfigurationError("CA file does not match the reviewed file pin")
        if pem.count(_PEM_CERT_BEGIN) != 1 or pem.count(_PEM_CERT_END) != 1:
            raise WorkerTLSConfigurationError("CA file is not the single reviewed certificate")
        der = ssl.PEM_cert_to_DER_cert(pem.decode("ascii"))
        if not hmac.compare_digest(hashlib.sha256(der).hexdigest(), expected_der_sha256.lower()):
            raise WorkerTLSConfigurationError("CA certificate does not match the reviewed identity")
        return pem
    except WorkerTLSConfigurationError:
        raise
    except (OSError, UnicodeError, ValueError, ssl.SSLError):
        raise WorkerTLSConfigurationError("CA file is missing or malformed") from None


def _context_from_verified_pem(pem: bytes) -> ssl.SSLContext:
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cadata=pem.decode("ascii"))
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        return context
    except (UnicodeError, ValueError, ssl.SSLError):
        raise WorkerTLSConfigurationError("CA cannot be loaded for server verification") from None


def _sealed_trust_descriptor(pem: bytes) -> int:
    """Create an immutable anonymous copy so libpq cannot follow a replaced path."""
    if not hasattr(os, "memfd_create"):
        raise WorkerTLSConfigurationError("immutable CA descriptor is unavailable")
    fd = -1
    try:
        fd = os.memfd_create("phase22-supabase-root-ca", os.MFD_ALLOW_SEALING)
        written = 0
        while written < len(pem):
            written += os.write(fd, pem[written:])
        seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, seals)
        os.lseek(fd, 0, os.SEEK_SET)
        os.set_inheritable(fd, True)
        return fd
    except (AttributeError, OSError):
        if fd >= 0:
            os.close(fd)
        raise WorkerTLSConfigurationError("immutable CA descriptor could not be prepared") from None


def _load_pinned_ca(
    ca_path: Path,
    expected_sha256: str = SUPABASE_ROOT_SHA256,
    expected_file_sha256: str = SUPABASE_ROOT_FILE_SHA256,
) -> ssl.SSLContext:
    """Validate the entire pinned file and build a context from those exact bytes."""
    try:
        fd = _open_absolute_nofollow(ca_path)
    except OSError:
        raise WorkerTLSConfigurationError("CA file is missing or malformed") from None
    try:
        pem = _read_verified_ca_fd(
            fd,
            expected_der_sha256=expected_sha256,
            expected_file_sha256=expected_file_sha256,
        )
    finally:
        os.close(fd)
    return _context_from_verified_pem(pem)


def _validate_effective_connection(configured: str, sslrootcert: str) -> None:
    """Check libpq's parsed values, not just the textual URL representation."""
    try:
        psycopg_uri = configured.replace("postgresql+psycopg://", "postgresql://", 1)
        effective = conninfo_to_dict(psycopg_uri)
    except (TypeError, ValueError):
        raise WorkerTLSConfigurationError("database URL could not be validated") from None

    expected = {
        "host": EXPECTED_HOST,
        "port": str(EXPECTED_PORT),
        "user": EXPECTED_USER,
        "dbname": EXPECTED_DATABASE,
        "sslmode": "verify-full",
        "gssencmode": "disable",
        "sslrootcert": sslrootcert,
    }
    if any(effective.get(key) != value for key, value in expected.items()):
        raise WorkerTLSConfigurationError("effective database connection identity is invalid")
    if not effective.get("password"):
        raise WorkerTLSConfigurationError("database URL is missing required connection fields")


def _normalize_database_url(database_url: str, sslrootcert: str) -> str:
    if (
        not isinstance(database_url, str)
        or not database_url
        or any(ord(ch) <= 0x20 or ord(ch) == 0x7F for ch in database_url)
    ):
        raise WorkerTLSConfigurationError("database URL is absent or malformed")
    if _BAD_PERCENT_ESCAPE.search(database_url):
        raise WorkerTLSConfigurationError("database URL is malformed")

    try:
        parsed = urlsplit(database_url)
        url = make_url(database_url)
        if parsed.scheme not in {"postgresql", "postgresql+psycopg"}:
            raise WorkerTLSConfigurationError("unsupported database URL scheme")
        if parsed.fragment or not parsed.netloc or "@" not in parsed.netloc:
            raise WorkerTLSConfigurationError("database URL is missing required connection fields")
        if parsed.netloc.count("@") != 1 or parsed.netloc.startswith("@"):
            raise WorkerTLSConfigurationError("database URL authority is ambiguous")
        if parsed.hostname != EXPECTED_HOST:
            raise WorkerTLSConfigurationError("database URL endpoint is not approved")
        if url.port != EXPECTED_PORT:
            raise WorkerTLSConfigurationError("database URL endpoint is not approved")
        if url.username != EXPECTED_USER or not url.password:
            raise WorkerTLSConfigurationError("database URL identity is not approved")
        if url.database != EXPECTED_DATABASE or parsed.path != "/postgres":
            raise WorkerTLSConfigurationError("database URL identity is not approved")
        if "," in parsed.netloc.split("@", 1)[1]:
            raise WorkerTLSConfigurationError("database URL authority is ambiguous")

        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        normalized_keys = [key.lower() for key, _ in pairs]
        if len(normalized_keys) != len(set(normalized_keys)):
            raise WorkerTLSConfigurationError("database URL has duplicate connection parameters")
        if any(key not in _ALLOWED_QUERY_KEYS for key in normalized_keys):
            raise WorkerTLSConfigurationError("database URL has an unapproved connection parameter")
        values = dict(pairs)
        if "gssencmode" in values and values["gssencmode"].lower() not in {"disable", "prefer", "require"}:
            raise WorkerTLSConfigurationError("database URL has an invalid GSS transport parameter")
        if "connect_timeout" in values:
            if not values["connect_timeout"].isdigit() or int(values["connect_timeout"]) < 1:
                raise WorkerTLSConfigurationError("database URL has an invalid connection parameter")
        if "application_name" in values and not values["application_name"]:
            raise WorkerTLSConfigurationError("database URL has an invalid connection parameter")

        query = [
            (key, value)
            for key, value in pairs
            if key.lower() not in {"sslmode", "gssencmode", "sslrootcert"}
        ]
        query.extend(
            (("sslmode", "verify-full"), ("gssencmode", "disable"), ("sslrootcert", sslrootcert))
        )
        configured = urlunsplit(parsed._replace(query=urlencode(query)))

        from app.db.session import normalize_database_url

        configured = normalize_database_url(configured)
        _validate_effective_connection(configured, sslrootcert)
        return configured
    except WorkerTLSConfigurationError:
        raise
    except Exception:
        raise WorkerTLSConfigurationError("database URL is malformed") from None


def _prepare_worker_environment(
    database_url: str,
    ca_path: Path,
    base_environment: dict[str, str],
    *,
    expected_sha256: str = SUPABASE_ROOT_SHA256,
    expected_file_sha256: str = SUPABASE_ROOT_FILE_SHA256,
) -> tuple[int, dict[str, str]]:
    """Pin an open trust-file descriptor and construct the worker-only environment."""
    source_fd = -1
    trust_fd = -1
    try:
        source_fd = _open_absolute_nofollow(ca_path)
        pem = _read_verified_ca_fd(
            source_fd,
            expected_der_sha256=expected_sha256,
            expected_file_sha256=expected_file_sha256,
        )
        _context_from_verified_pem(pem)
        trust_fd = _sealed_trust_descriptor(pem)
        fd_path = f"/proc/self/fd/{trust_fd}"
        if not Path(fd_path).exists():
            raise WorkerTLSConfigurationError("verified CA descriptor path is unavailable")
        configured_url = _normalize_database_url(database_url, fd_path)
        worker_environment = dict(base_environment)
        for variable in _LIBPQ_ENVIRONMENT_VARIABLES:
            worker_environment.pop(variable, None)
        worker_environment["DATABASE_URL"] = configured_url
        worker_environment["PGSSLMODE"] = "verify-full"
        worker_environment["PGGSSENCMODE"] = "disable"
        worker_environment["PGSSLROOTCERT"] = fd_path
        os.close(source_fd)
        source_fd = -1
        return trust_fd, worker_environment
    except WorkerTLSConfigurationError:
        if source_fd >= 0:
            os.close(source_fd)
        if trust_fd >= 0:
            os.close(trust_fd)
        raise
    except Exception:
        if source_fd >= 0:
            os.close(source_fd)
        if trust_fd >= 0:
            os.close(trust_fd)
        raise WorkerTLSConfigurationError("worker TLS preflight failed") from None


def run_worker() -> None:
    """Replace this preflight process with the existing single-job worker."""
    ca_fd: int | None = None
    try:
        workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve(strict=True)
        ca_path = workspace / CA_RELATIVE_PATH
        ca_fd, worker_environment = _prepare_worker_environment(
            os.environ.get("DATABASE_URL", ""),
            ca_path,
            dict(os.environ),
        )
        os.execvpe(
            sys.executable,
            [sys.executable, "-m", "app.jobs.worker_runner", "--once"],
            worker_environment,
        )
    except Exception:
        if ca_fd is not None:
            os.close(ca_fd)
        print("::error::Worker PostgreSQL TLS preflight failed; worker was not started", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    run_worker()
