"""Create first-run Windows credentials without printing any secret values."""
from __future__ import annotations

from pathlib import Path
import secrets
import sys

from werkzeug.security import generate_password_hash


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: create_local_secrets.py <protected-directory>")
    target = Path(sys.argv[1]).resolve()
    env_path = target / "central-comercial.env"
    password_path = target / "admin-password.txt"
    if env_path.exists() or password_path.exists():
        raise SystemExit("Local credentials already exist; refusing to overwrite them.")

    password = secrets.token_urlsafe(24)
    session_secret = secrets.token_urlsafe(48)
    env_contents = "\n".join((
        "CENTRAL_ADMIN_PASSWORD_HASH=" + generate_password_hash(password, method="scrypt"),
        "CENTRAL_SESSION_SECRET=" + session_secret,
        "CENTRAL_PUBLIC_ORIGIN=http://127.0.0.1:8765",
        "CENTRAL_BIND=127.0.0.1",
        "CENTRAL_PORT=8765",
        "CENTRAL_PDF_MAX_BYTES=8388608",
        "CENTRAL_TRUSTED_PROXY_HOPS=0",
        "LARK_SMTP_USER=",
        "LARK_SMTP_APP_PASSWORD=",
        "",
    ))
    env_path.write_text(env_contents, encoding="utf-8", newline="\n")
    password_path.write_text(password + "\n", encoding="utf-8", newline="\n")
    print("Created protected local environment and admin-password files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
