"""Central Comercial Tec Escola: painel privado de propostas via Lark.

Execucao local: python -m central_comercial
Credenciais sempre por ambiente; nenhuma rota publica dispara e-mails.
"""
from __future__ import annotations

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
import threading
import time
from urllib.parse import urlsplit

from flask import Flask, abort, jsonify, make_response, redirect, render_template, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).resolve().parent.parent
TEMPLATES = {
    "institucional": ("apresentacao-institucional.html", "Conheça a Tec Escola"),
    "proposta": ("propostacomercial-pronta.html", "Sua proposta comercial Tec Escola está pronta"),
}
DEFAULT_PDF_LIMIT = 8 * 1024 * 1024
MAX_PDF_LIMIT = 25 * 1024 * 1024
UPLOAD_OVERHEAD = 256 * 1024
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


def field(
    value: str,
    name: str,
    limit: int = 120,
    required: bool = True,
    multiline: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ValueError(name + " inválido.")
    if multiline:
        value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = value.strip()
    invalid_control = any(
        (ord(char) < 32 and not (multiline and char in "\n\t")) or ord(char) == 127
        for char in value
    )
    if (required and not value) or len(value) > limit or invalid_control:
        raise ValueError(name + " inválido.")
    return value


def render_email(
    template_id: str,
    responsavel: str,
    instituicao: str,
    consultor: str,
    mensagem: str = "",
) -> str:
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
    if mensagem:
        safe_message = html.escape(mensagem, quote=True).replace("\n", "<br>\n")
        paragraph = (
            '<p style="margin:16px 0 0; font-size:15px; line-height:24px; color:#425772;">'
            + safe_message + "</p>"
        )
        escaped_name = re.escape(html.escape(responsavel, quote=True))
        greeting = re.compile(
            r"(<p\b[^>]*>\s*Olá,\s*<strong>" + escaped_name + r"</strong>!\s*</p>)",
            re.IGNORECASE,
        )
        result, inserted = greeting.subn(lambda match: match.group(1) + "\n" + paragraph, result, count=1)
        if inserted != 1:
            raise RuntimeError("Não foi possível inserir a mensagem complementar no modelo.")
    return result


def is_pdf(data: bytes) -> bool:
    """Confere cabeçalho PDF (até 1 KiB) e marcador final, sem executar nem gravar o arquivo."""
    if not data:
        return False
    header = re.search(rb"%PDF-(?:1\.[0-7]|2\.0)", data[:1024])
    tail = data[-1024:]
    eof = re.search(rb"%%EOF[\x00\x09\x0a\x0c\x0d\x20]*$", tail)
    return header is not None and eof is not None


def compose_message(data: dict, sender: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr(("Tec Escola", sender))
    msg["To"] = data["destinatario"]
    msg["Subject"] = data["assunto"]
    plain = "Olá, " + data["responsavel"] + "!\n\n"
    if data.get("mensagem"):
        plain += data["mensagem"] + "\n\n"
    plain += "Segue o material da Tec Escola em anexo.\n"
    msg.set_content(plain)
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
    app.config["TESTING"] = testing
    app.config["SEND_MAIL"] = deliver_lark

    raw_pdf_limit = os.environ.get("CENTRAL_PDF_MAX_BYTES", str(DEFAULT_PDF_LIMIT))
    try:
        pdf_limit = int(raw_pdf_limit)
    except ValueError as exc:
        raise RuntimeError("CENTRAL_PDF_MAX_BYTES deve ser um inteiro em bytes.") from exc
    if not 1024 <= pdf_limit <= MAX_PDF_LIMIT:
        raise RuntimeError("CENTRAL_PDF_MAX_BYTES deve ficar entre 1024 e 26214400 bytes.")
    app.config["PDF_MAX_BYTES"] = pdf_limit
    app.config["PDF_MAX_MB_LABEL"] = f"{pdf_limit / (1024 * 1024):g}"
    app.config["MAX_CONTENT_LENGTH"] = pdf_limit + UPLOAD_OVERHEAD

    expected_origin = os.environ.get("CENTRAL_PUBLIC_ORIGIN", "http://127.0.0.1:8765").rstrip("/")
    parsed_origin = urlsplit(expected_origin)
    if (parsed_origin.scheme not in ("http", "https") or not parsed_origin.netloc
            or parsed_origin.username or parsed_origin.password
            or parsed_origin.path or parsed_origin.query or parsed_origin.fragment):
        raise RuntimeError("CENTRAL_PUBLIC_ORIGIN deve conter apenas origem, sem caminho.")
    app.config["PUBLIC_ORIGIN"] = expected_origin
    # O mesmo fail-closed vale para execução por WSGI, não apenas pelo comando CLI.
    secret = os.getenv("CENTRAL_SESSION_SECRET", "")
    if not testing and (len(secret) < 32 or not os.getenv("CENTRAL_ADMIN_PASSWORD_HASH", "")):
        raise RuntimeError("Configure o hash de acesso e o segredo de sessão antes de iniciar.")
    if not secret:
        secret = secrets.token_urlsafe(48)

    raw_proxy_hops = os.environ.get("CENTRAL_TRUSTED_PROXY_HOPS", "0")
    try:
        trusted_proxy_hops = int(raw_proxy_hops)
    except ValueError as exc:
        raise RuntimeError("CENTRAL_TRUSTED_PROXY_HOPS deve ser um inteiro não negativo.") from exc
    if trusted_proxy_hops < 0 or trusted_proxy_hops > 3:
        raise RuntimeError("CENTRAL_TRUSTED_PROXY_HOPS deve ficar entre 0 e 3.")
    if trusted_proxy_hops:
        # Só confia no IP encaminhado por um proxy explicitamente declarado; Host continua validado.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=trusted_proxy_hops)

    # Estado de uma instancia: sem dados de clientes ou PDFs gravados em disco.
    sessions: dict[str, dict] = {}
    drafts: dict[str, dict] = {}
    failed_logins: dict[str, deque] = {}
    recent_sends: deque = deque()
    audit: deque = deque(maxlen=40)
    state_lock = threading.Lock()
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
        if len(raw_cookie) > 256 or "." not in raw_cookie:
            return None
        key, supplied_signature = raw_cookie.rsplit(".", 1)
        try:
            correct_signature = signed_session(key).rsplit(".", 1)[1]
        except UnicodeEncodeError:
            return None
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
        if request.host.lower() != parsed_origin.netloc.lower():
            abort(400)
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and not check_origin():
            abort(403)

    @app.after_request
    def secure_headers(response):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["X-Content-Type-Options"] = "nosniff"
        # `no-referrer` turns Origin into `null` on basic form POSTs in browsers.
        # This policy keeps same-origin Origin checks usable and limits cross-origin referrers.
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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
        return jsonify(error=f"Envio muito grande (PDF limitado a {app.config['PDF_MAX_MB_LABEL']} MB)."), 413

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
        with state_lock:
            sessions.pop(sid, None)
            for key, draft in list(drafts.items()):
                if draft["owner"] == sid:
                    drafts.pop(key, None)
            retained_audit = [entry for entry in audit if entry["owner"] != sid]
            audit.clear()
            audit.extend(retained_audit)
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
            history=[entry for entry in audit if entry["owner"] == active[0]][:5],
            pdf_limit_mb=app.config["PDF_MAX_MB_LABEL"],
            pdf_limit_bytes=app.config["PDF_MAX_BYTES"],
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
            mensagem = field(request.form.get("mensagem", ""), "Mensagem complementar", 2000,
                             required=False, multiline=True)
            upload = request.files.get("pdf")
            if upload is None or not upload.filename:
                raise ValueError("Anexe o PDF citado no modelo.")
            client_filename = upload.filename.replace("\\", "/").split("/")[-1]
            pdf_nome = field(secure_filename(client_filename), "Nome do PDF", 120)
            if not pdf_nome.lower().endswith(".pdf"):
                raise ValueError("O anexo deve ser um PDF.")
            pdf_data = upload.stream.read(app.config["PDF_MAX_BYTES"] + 1)
            if len(pdf_data) > app.config["PDF_MAX_BYTES"]:
                raise ValueError("PDF maior que o limite configurado.")
            if not is_pdf(pdf_data):
                raise ValueError("O arquivo não parece ser um PDF válido.")
            html_body = render_email(template_id, responsavel, instituicao, consultor, mensagem)
        except (ValueError, UnicodeError) as exc:
            return jsonify(error=str(exc)), 400

        # Limita rascunhos em memoria e garante que pertencam a esta sessao.
        with state_lock:
            for key, old in list(drafts.items()):
                if old["expires"] < now() or old["owner"] == sid:
                    drafts.pop(key, None)
            draft_id = secrets.token_urlsafe(32)
            drafts[draft_id] = {
                "owner": sid, "expires": now() + DRAFT_TTL,
                "template": template_id,
                "destinatario": destinatario, "responsavel": responsavel,
                "instituicao": instituicao, "consultor": consultor,
                "assunto": assunto, "mensagem": mensagem, "html": html_body,
                "pdf_nome": pdf_nome, "pdf": pdf_data,
            }
        return jsonify(
            draft_id=draft_id, html=html_body, destinatario=destinatario,
            assunto=assunto, pdf_nome=pdf_nome, pdf_tamanho=len(pdf_data),
            expira_em_minutos=10,
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
        username = os.getenv("LARK_SMTP_USER", "")
        password = os.getenv("LARK_SMTP_APP_PASSWORD", "")
        if not valid_email(username) or not password:
            return jsonify(error="Lark SMTP ainda não configurado no servidor."), 503
        with state_lock:
            draft = drafts.get(draft_id)
            if not draft or draft["owner"] != sid or draft["expires"] < now():
                return jsonify(error="Prévia expirada. Gere novamente antes do envio."), 409
            while recent_sends and now() - recent_sends[0] > SEND_WINDOW:
                recent_sends.popleft()
            if len(recent_sends) >= 20:
                return jsonify(error="Limite de 20 tentativas por hora atingido."), 429
            # Reserva atomicamente antes do SMTP; uma segunda requisição não pode reutilizar o rascunho.
            drafts.pop(draft_id, None)
            recent_sends.append(now())
        try:
            message = compose_message(draft, username)
            app.config["SEND_MAIL"](message, username, password)
        except smtplib.SMTPAuthenticationError:
            audit.appendleft({"quando": datetime.now(timezone.utc).isoformat(),
                              "modelo": draft["template"], "status": "falha_autenticacao", "owner": sid})
            app.logger.warning("Envio SMTP falhou (sem dados do destinatário).")
            return jsonify(error="A autenticação SMTP do Lark falhou. Confira a conta, a senha dedicada e a liberação de clientes externos."), 502
        except (OSError, ssl.SSLError, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected):
            audit.appendleft({"quando": datetime.now(timezone.utc).isoformat(),
                              "modelo": draft["template"], "status": "falha_conexao", "owner": sid})
            app.logger.warning("Envio SMTP falhou (sem dados do destinatário).")
            return jsonify(error="Não foi possível concluir a conexão SMTP do Lark. Verifique rede e configuração; gere uma nova prévia antes de tentar novamente."), 502
        except (smtplib.SMTPException, ValueError):
            audit.appendleft({"quando": datetime.now(timezone.utc).isoformat(),
                              "modelo": draft["template"], "status": "falha_servidor", "owner": sid})
            app.logger.warning("Envio SMTP falhou (sem dados do destinatário).")
            return jsonify(error="O servidor SMTP do Lark rejeitou a mensagem. Confira o remetente e o limite de envio."), 502

        audit.appendleft({"quando": datetime.now(timezone.utc).isoformat(),
                          "modelo": draft["template"], "status": "aceito_pelo_smtp", "owner": sid})
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
