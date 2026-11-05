"""Central Comercial Tec Escola: painel privado de propostas via Lark.

Execucao local: python -m central_comercial
Credenciais sempre por ambiente; nenhuma rota publica dispara e-mails.
"""
from __future__ import annotations

import base64
from collections import deque
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import smtplib
import ssl
import time
from urllib.parse import urlsplit

from flask import Flask, abort, jsonify, make_response, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).resolve().parent.parent
TEMPLATES = {
    "institucional": ("apresentacao-institucional.html", "Conheça a Tec Escola"),
    "proposta": ("propostacomercial-pronta.html", "Sua proposta comercial Tec Escola está pronta"),
}
PDF_LIMIT = 8 * 1024 * 1024
BODY_LIMIT = 10 * 1024 * 1024
SESSION_TTL = 8 * 60 * 60
DRAFT_TTL = 10 * 60
LOGIN_WINDOW = 15 * 60
SEND_WINDOW = 60 * 60


def valid_email(value: str) -> bool:
    if not isinstance(value, str) or len(value) > 254 or any(ord(c) < 33 for c in value):
        return False
    if parseaddr(value)[1] != value:
        return False
    return re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", value) is not None


def field(value: str, name: str, limit: int = 120, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(name + " inválido.")
    value = value.strip()
    if (required and not value) or len(value) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(name + " inválido.")
    return value


def render_email(template_id: str, responsavel: str, instituicao: str, consultor: str) -> str:
    import html

    file_name = TEMPLATES[template_id][0]
    result = (BASE / file_name).read_text(encoding="utf-8")
    replacements = {
        "[Nome do responsável]": responsavel,
        "[Nome da instituição]": instituicao,
        "[Nome do consultor]": consultor,
    }
    for marker, value in replacements.items():
        result = result.replace(marker, html.escape(value, quote=True))
    return result


def compose_message(data: dict, sender: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr(("Tec Escola", sender))
    msg["To"] = data["destinatario"]
    msg["Subject"] = data["assunto"]
    msg.set_content(
        "Olá, " + data["responsavel"] + "!\n\n"
        "Segue o material da Tec Escola em anexo.\n"
    )
    msg.add_alternative(data["html"], subtype="html", charset="utf-8")
    msg.add_attachment(data["pdf"], maintype="application", subtype="pdf", filename=data["pdf_nome"])
    return msg


def deliver_lark(message: EmailMessage, username: str, app_password: str) -> None:
    """SMTP com TLS verificado, compartilhando o mesmo transporte do enviador CLI."""
    with smtplib.SMTP_SSL(
        "smtp.larksuite.com", 465, timeout=25, context=ssl.create_default_context()
    ) as smtp:
        smtp.login(username, app_password)
        smtp.send_message(message)


def create_app(*, testing: bool = False) -> Flask:
    app = Flask(__name__, template_folder=str(BASE / "central_comercial" / "templates"),
                static_folder=str(BASE / "central_comercial" / "static"))
    app.config["MAX_CONTENT_LENGTH"] = BODY_LIMIT
    app.config["TESTING"] = testing
    app.config["SEND_MAIL"] = deliver_lark

    expected_origin = os.environ.get("CENTRAL_PUBLIC_ORIGIN", "http://127.0.0.1:8765").rstrip("/")
    parsed_origin = urlsplit(expected_origin)
    if (parsed_origin.scheme not in ("http", "https") or not parsed_origin.netloc
            or parsed_origin.path or parsed_origin.query or parsed_origin.fragment):
        raise RuntimeError("CENTRAL_PUBLIC_ORIGIN deve conter apenas origem, sem caminho.")
    app.config["PUBLIC_ORIGIN"] = expected_origin
    # O mesmo fail-closed vale para execução por WSGI, não apenas pelo comando CLI.
    secret = os.getenv("CENTRAL_SESSION_SECRET", "")
    if not testing and (len(secret) < 32 or not os.getenv("CENTRAL_ADMIN_PASSWORD_HASH", "")):
        raise RuntimeError("Configure o hash de acesso e o segredo de sessão antes de iniciar.")
    if not secret:
        secret = secrets.token_urlsafe(48)

    # Estado de uma instancia: sem dados de clientes ou PDFs gravados em disco.
    sessions: dict[str, dict] = {}
    drafts: dict[str, dict] = {}
    failed_logins: dict[str, deque] = {}
    recent_sends: deque = deque()
    audit: deque = deque(maxlen=40)
    app.extensions["central_state"] = {
        "sessions": sessions, "drafts": drafts, "audit": audit,
    }
    cookie_name = "__Host-central_session" if parsed_origin.scheme == "https" else "central_session"

    def signed_session(sid: str) -> str:
        signature = hmac.new(secret.encode("utf-8"), sid.encode("ascii"), hashlib.sha256).hexdigest()
        return sid + "." + signature

    def now() -> float:
        return time.time()

    def identity() -> tuple[str, dict] | None:
        raw_cookie = request.cookies.get(cookie_name, "")
        if "." not in raw_cookie:
            return None
        key, supplied_signature = raw_cookie.rsplit(".", 1)
        correct_signature = signed_session(key).rsplit(".", 1)[1]
        if not hmac.compare_digest(supplied_signature, correct_signature):
            return None
        item = sessions.get(key)
        if item and item["expires"] > now():
            return key, item
        if key:
            sessions.pop(key, None)
        return None

    def csrf_check(item: dict) -> bool:
        supplied = request.headers.get("X-CSRF-Token", "")
        return bool(supplied and hmac.compare_digest(supplied, item["csrf"]))

    def auth_required() -> tuple[str, dict]:
        active = identity()
        if active is None:
            abort(401)
        return active

    def check_origin() -> bool:
        return request.headers.get("Origin") == expected_origin

    @app.before_request
    def enforce_host_and_origin():
        if request.host != parsed_origin.netloc:
            abort(400)
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and not check_origin():
            abort(403)

    @app.after_request
    def secure_headers(response):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' https: data:; connect-src 'self'; frame-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        if parsed_origin.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="Arquivo muito grande (máximo 8 MB para PDF)."), 413

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify(error="Sessão expirada. Entre novamente."), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify(error="Requisição não autorizada."), 403

    @app.get("/healthz")
    def health():
        return ("ok", 200, {"Content-Type": "text/plain; charset=utf-8"})

    @app.get("/login")
    def login_page():
        if identity() is not None:
            return redirect(url_for("dashboard"))
        return render_template("login.html", error=None)

    @app.post("/login")
    def login():
        ip = request.remote_addr or "unknown"
        failures = failed_logins.setdefault(ip, deque())
        while failures and now() - failures[0] > LOGIN_WINDOW:
            failures.popleft()
        if len(failures) >= 6:
            return render_template("login.html", error="Muitas tentativas. Tente mais tarde."), 429

        stored_hash = os.getenv("CENTRAL_ADMIN_PASSWORD_HASH", "")
        password = request.form.get("password", "")
        if not stored_hash or not password or not check_password_hash(stored_hash, password):
            failures.append(now())
            return render_template("login.html", error="Senha inválida."), 401

        failures.clear()
        sid = secrets.token_urlsafe(32)
        sessions[sid] = {"csrf": secrets.token_urlsafe(32), "expires": now() + SESSION_TTL}
        response = make_response(redirect(url_for("dashboard")))
        response.set_cookie(
            cookie_name, signed_session(sid), secure=(parsed_origin.scheme == "https"),
            httponly=True, samesite="Strict", path="/", max_age=SESSION_TTL,
        )
        return response

    @app.post("/logout")
    def logout():
        sid, item = auth_required()
        if not csrf_check(item):
            abort(403)
        sessions.pop(sid, None)
        for key, draft in list(drafts.items()):
            if draft["owner"] == sid:
                drafts.pop(key, None)
        response = make_response(redirect(url_for("login_page")))
        response.delete_cookie(cookie_name, path="/")
        return response

    @app.get("/")
    def dashboard():
        active = identity()
        if active is None:
            return redirect(url_for("login_page"))
        _, item = active
        return render_template(
            "dashboard.html", csrf=item["csrf"],
            templates=TEMPLATES, smtp_ready=bool(
                valid_email(os.getenv("LARK_SMTP_USER", ""))
                and os.getenv("LARK_SMTP_APP_PASSWORD", "")
            ),
        )

    @app.post("/api/preview")
    def preview():
        sid, item = auth_required()
        if not csrf_check(item):
            abort(403)
        try:
            template_id = field(request.form.get("template", ""), "Modelo", 30)
            if template_id not in TEMPLATES:
                raise ValueError("Modelo inválido.")
            destinatario = field(request.form.get("destinatario", ""), "Destinatário", 254)
            if not valid_email(destinatario):
                raise ValueError("Informe um único e-mail válido.")
            responsavel = field(request.form.get("responsavel", ""), "Responsável")
            instituicao = field(request.form.get("instituicao", ""), "Instituição", required=False) or "sua instituição"
            consultor = field(request.form.get("consultor", ""), "Consultor", required=False) or "Equipe Comercial"
            assunto = field(request.form.get("assunto", ""), "Assunto", 160)
            upload = request.files.get("pdf")
            if upload is None or not upload.filename:
                raise ValueError("Anexe o PDF citado no modelo.")
            pdf_nome = field(upload.filename.replace("\\", "/").split("/")[-1], "Nome do PDF", 120)
            if not pdf_nome.lower().endswith(".pdf"):
                raise ValueError("O anexo deve ser um PDF.")
            pdf_data = upload.stream.read(PDF_LIMIT + 1)
            if len(pdf_data) > PDF_LIMIT or not pdf_data.startswith(b"%PDF-"):
                raise ValueError("PDF inválido ou maior que 8 MB.")
            html_body = render_email(template_id, responsavel, instituicao, consultor)
        except (ValueError, UnicodeError) as exc:
            return jsonify(error=str(exc)), 400

        # Limita rascunhos em memoria e garante que pertencam a esta sessao.
        for key, old in list(drafts.items()):
            if old["expires"] < now() or old["owner"] == sid:
                drafts.pop(key, None)
        draft_id = secrets.token_urlsafe(32)
        drafts[draft_id] = {
            "owner": sid, "expires": now() + DRAFT_TTL,
            "template": template_id,
            "destinatario": destinatario, "responsavel": responsavel,
            "instituicao": instituicao, "consultor": consultor,
            "assunto": assunto, "html": html_body,
            "pdf_nome": pdf_nome, "pdf": pdf_data,
        }
        return jsonify(
            draft_id=draft_id, html=html_body, destinatario=destinatario,
            assunto=assunto, pdf_nome=pdf_nome,
            pdf_tamanho=len(pdf_data), expira_em_minutos=10,
        )

    @app.post("/api/send")
    def send():
        sid, item = auth_required()
        if not csrf_check(item):
            abort(403)
        incoming = request.get_json(silent=True)
        if not isinstance(incoming, dict) or incoming.get("confirmacao") != "ENVIAR":
            return jsonify(error="Confirmação explícita obrigatória."), 400
        draft_id = incoming.get("draft_id", "")
        if not isinstance(draft_id, str):
            return jsonify(error="Prévia inválida."), 400
        draft = drafts.get(draft_id)
        if not draft or draft["owner"] != sid or draft["expires"] < now():
            return jsonify(error="Prévia expirada. Gere novamente antes do envio."), 409

        while recent_sends and now() - recent_sends[0] > SEND_WINDOW:
            recent_sends.popleft()
        if len(recent_sends) >= 20:
            return jsonify(error="Limite de 20 tentativas por hora atingido."), 429
        # Consome antes do SMTP, impedindo duplo clique e reuso.
        drafts.pop(draft_id, None)
        recent_sends.append(now())

        username = os.getenv("LARK_SMTP_USER", "")
        password = os.getenv("LARK_SMTP_APP_PASSWORD", "")
        if not valid_email(username) or not password:
            return jsonify(error="Lark SMTP ainda não configurado no servidor."), 503
        try:
            message = compose_message(draft, username)
            app.config["SEND_MAIL"](message, username, password)
        except (OSError, smtplib.SMTPException, ValueError):
            audit.appendleft({"quando": datetime.now(timezone.utc).isoformat(),
                              "modelo": draft["template"], "status": "falha"})
            app.logger.warning("Envio SMTP falhou (sem dados do destinatário).")
            return jsonify(error="Falha no Lark SMTP. Verifique a configuração e tente uma nova prévia."), 502

        audit.appendleft({"quando": datetime.now(timezone.utc).isoformat(),
                          "modelo": draft["template"], "status": "aceito_pelo_smtp"})
        return jsonify(status="aceito_pelo_smtp",
                       message="Lark aceitou o envio. Isso não garante a entrega ao destinatário.")

    return app


def main() -> None:
    import getpass
    import sys

    if len(sys.argv) == 2 and sys.argv[1] == "hash-password":
        first = getpass.getpass("Senha de acesso: ")
        second = getpass.getpass("Repita a senha: ")
        if len(first) < 12 or first != second:
            raise SystemExit("Use no mínimo 12 caracteres e duas entradas idênticas.")
        print(generate_password_hash(first, method="scrypt"))
        return
    if len(sys.argv) == 2 and sys.argv[1] == "generate-secret":
        print(secrets.token_urlsafe(48))
        return
    if len(sys.argv) > 1:
        raise SystemExit("Uso: python -m central_comercial [hash-password|generate-secret]")

    if not os.getenv("CENTRAL_ADMIN_PASSWORD_HASH"):
        raise SystemExit("Falta CENTRAL_ADMIN_PASSWORD_HASH.")
    secret = os.getenv("CENTRAL_SESSION_SECRET", "")
    if len(secret) < 32:
        raise SystemExit("CENTRAL_SESSION_SECRET exige no mínimo 32 caracteres.")
    bind = os.getenv("CENTRAL_BIND", "127.0.0.1")
    origin = os.getenv("CENTRAL_PUBLIC_ORIGIN", "http://127.0.0.1:8765")
    if bind not in ("127.0.0.1", "::1", "localhost") and urlsplit(origin).scheme != "https":
        raise SystemExit("Acesso remoto exige CENTRAL_PUBLIC_ORIGIN=https://... e proxy TLS.")
    app = create_app()
    app.run(host=bind, port=int(os.getenv("CENTRAL_PORT", "8765")), debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
