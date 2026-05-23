"""mTLS Certificate Authority — generate CA, issue node certs, manage CRL."""

import subprocess
from pathlib import Path

from config import settings

CERTS_DIR = Path(settings.ca_cert_path).parent.resolve()


def _run(cmd: list[str]) -> str:
    """Run openssl command, return stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def generate_ca() -> None:
    """Create self-signed CA certificate and key."""
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    ca_key = CERTS_DIR / "ca.key"
    ca_crt = CERTS_DIR / "ca.crt"

    if ca_crt.exists():
        return  # Already exists

    _run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:4096",
            "-keyout",
            str(ca_key),
            "-out",
            str(ca_crt),
            "-days",
            "3650",
            "-nodes",
            "-subj",
            "/C=CN/O=Tongrui/CN=Tongrui Root CA",
        ]
    )
    # Also generate server cert for coordinator
    issue_cert("coordinator", is_server=True)


def issue_cert(node_id: str, is_server: bool = False) -> tuple[Path, Path]:
    """Issue a certificate for a node. Returns (cert_path, key_path)."""
    node_key = CERTS_DIR / f"{node_id}.key"
    node_csr = CERTS_DIR / f"{node_id}.csr"
    node_crt = CERTS_DIR / f"{node_id}.crt"

    # Generate private key
    _run(["openssl", "genrsa", "-out", str(node_key), "2048"])

    # Generate CSR
    subj = f"/C=CN/O=Tongrui/CN={node_id}"
    cmd = [
        "openssl",
        "req",
        "-new",
        "-key",
        str(node_key),
        "-out",
        str(node_csr),
        "-subj",
        subj,
    ]
    _run(cmd)

    # Sign with CA
    sign_cmd = [
        "openssl",
        "x509",
        "-req",
        "-in",
        str(node_csr),
        "-CA",
        str(CERTS_DIR / "ca.crt"),
        "-CAkey",
        str(CERTS_DIR / "ca.key"),
        "-CAcreateserial",
        "-out",
        str(node_crt),
        "-days",
        "365",
    ]
    _run(sign_cmd)

    # Clean up CSR
    node_csr.unlink(missing_ok=True)

    return node_crt, node_key


def revoke_cert(node_id: str) -> None:
    """Revoke a node certificate and update CRL."""
    node_crt = CERTS_DIR / f"{node_id}.crt"
    crl = CERTS_DIR / "ca.crl"

    _run(
        [
            "openssl",
            "ca",
            "-revoke",
            str(node_crt),
            "-keyfile",
            str(CERTS_DIR / "ca.key"),
            "-cert",
            str(CERTS_DIR / "ca.crt"),
            "-config",
            "/etc/ssl/openssl.cnf",
        ]
    )
    _run(
        [
            "openssl",
            "ca",
            "-gencrl",
            "-keyfile",
            str(CERTS_DIR / "ca.key"),
            "-cert",
            str(CERTS_DIR / "ca.crt"),
            "-out",
            str(crl),
            "-config",
            "/etc/ssl/openssl.cnf",
        ]
    )


def verify_cert(cert_path: str | Path) -> bool:
    """Verify a certificate was signed by our CA."""
    try:
        _run(
            [
                "openssl",
                "verify",
                "-CAfile",
                str(CERTS_DIR / "ca.crt"),
                str(cert_path),
            ]
        )
        return True
    except subprocess.CalledProcessError:
        return False
