import io
import os
import smtplib
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from central_comercial import create_app, render_email, valid_email

ORIGIN = "http://127.0.0.1:8765"
PASSWORD = "test-password-not-for-production"
PDF = b"%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF\n"


class CentralTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "CENTRAL_PUBLIC_ORIGIN": ORIGIN,
            "CENTRAL_ADMIN_PASSWORD_HASH": generate_password_hash(
                PASSWORD, method="pbkdf2:sha256:1000"),
            "CENTRAL_SESSION_SECRET": "testing-secret-123456789012345678901234",
            "CENTRAL_TRUSTED_PROXY_HOPS": "0",
            "LARK_SMTP_USER": "comercial@example.com",
            "LARK_SMTP_APP_PASSWORD": "dummy-nonprod",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.app = create_app(testing=True)
        self.app.config["SERVER_NAME"] = "127.0.0.1:8765"
        self.sent = []
        self.app.config["SEND_MAIL"] = lambda *args: self.sent.append(args)
        self.client = self.app.test_client()
        self.client.environ_base["HTTP_HOST"] = "127.0.0.1:8765"

    def login(self, client=None):
        client = client or self.client
        response = client.post("/login", data={"password": PASSWORD},
                               headers={"Origin": ORIGIN})
        self.assertEqual(response.status_code, 302)
        cookie = response.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        state = self.app.extensions["central_state"]["sessions"]
        return next(reversed(state.values()))["csrf"]

    def preview(self, csrf, *, client=None, pdf=PDF, filename="proposta.pdf",
                email="direcao@example.com", mensagem=""):
        return (client or self.client).post("/api/preview", data={
            "template": "proposta",
            "destinatario": email,
            "responsavel": "Ana & Bia",
            "instituicao": "Escola <Beta>",
            "consultor": "Equipe",
            "assunto": "Proposta Escola Beta",
            "mensagem": mensagem,
            "pdf": (io.BytesIO(pdf), filename),
        }, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})

    def send(self, csrf, draft, *, client=None, confirm="ENVIAR"):
        return (client or self.client).post(
            "/api/send", json={"draft_id": draft, "confirmacao": confirm},
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        )

    def test_login_and_private_routes(self):
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.post("/api/preview").status_code, 403)
        response = self.client.post("/api/send", json={"confirmacao": "ENVIAR"},
                                    headers={"Origin": ORIGIN})
        self.assertEqual(response.status_code, 401)

    def test_wrong_password_rate_limit(self):
        for _ in range(6):
            response = self.client.post("/login", data={"password": "wrong"},
                                        headers={"Origin": ORIGIN})
            self.assertEqual(response.status_code, 401)
        response = self.client.post("/login", data={"password": PASSWORD},
                                    headers={"Origin": ORIGIN})
        self.assertEqual(response.status_code, 429)

    def test_origin_csrf_and_host_protection(self):
        self.login()
        self.assertEqual(self.client.post("/api/preview").status_code, 403)
        self.assertEqual(self.client.post("/api/preview", headers={
            "Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.get("/", headers={"Host": "evil.example"}).status_code, 400)
        response = self.client.post("/api/preview", headers={"Origin": ORIGIN})
        self.assertEqual(response.status_code, 403)

    def test_https_cookie_and_security_headers(self):
        secure_origin = "https://central.example"
        with patch.dict(os.environ, {"CENTRAL_PUBLIC_ORIGIN": secure_origin}):
            app = create_app(testing=True)
        app.config["SERVER_NAME"] = "central.example"
        client = app.test_client()
        client.environ_base["HTTP_HOST"] = "central.example"
        response = client.post("/login", data={"password": PASSWORD},
                               headers={"Origin": secure_origin}, base_url=secure_origin)
        self.assertEqual(response.status_code, 302)
        cookie = response.headers["Set-Cookie"]
        self.assertIn("__Host-central_session", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Path=/", cookie)
        self.assertIn("SameSite=Strict", cookie)
        page = client.get("/login", base_url=secure_origin)
        self.assertIn("no-store", page.headers["Cache-Control"])
        self.assertEqual(page.headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(page.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(page.headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", page.headers["Content-Security-Policy"])
        self.assertIn("max-age=31536000", page.headers["Strict-Transport-Security"])

    def test_expired_session_is_rejected(self):
        self.login()
        sessions = self.app.extensions["central_state"]["sessions"]
        session = next(iter(sessions.values()))
        session["expires"] = time.time() - 1
        response = self.client.post("/api/send", json={}, headers={"Origin": ORIGIN})
        self.assertEqual(response.status_code, 401)

    def test_logout_revokes_session_and_clears_owned_history(self):
        csrf = self.login()
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.client.post("/logout", headers={
            "Origin": ORIGIN, "X-CSRF-Token": csrf,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_email_validation_and_single_recipient(self):
        self.assertTrue(valid_email("ana.silva+vendas@example.com.br"))
        for address in ("A <ana@example.com>", "a@example.com,b@example.com",
                        "a@example.com; b@example.com", "a@example.com\r\nBcc:x@y.com",
                        "a@localhost", " a@example.com"):
            self.assertFalse(valid_email(address), address)
        csrf = self.login()
        self.assertEqual(self.preview(csrf, email="a@example.com,b@example.com").status_code, 400)

    def test_models_escape_personalization_and_message(self):
        institutional = render_email("institucional", "A & B", "Escola <Beta>",
                                     "Equipe \"Azul\"", "Olá <script>\nTudo bem?")
        proposal = render_email("proposta", "A & B", "Escola <Beta>", "Equipe",
                                "Olá <script>\nTudo bem?")
        for body in (institutional, proposal):
            self.assertIn("A &amp; B", body)
            self.assertIn("Olá &lt;script&gt;<br>\nTudo bem?", body)
            self.assertNotIn("[Nome do responsável]", body)
            self.assertNotIn("<script>", body)
        self.assertIn("Escola &lt;Beta&gt;", proposal)
        self.assertNotIn("[Nome da instituição]", proposal)
        self.assertIn("Equipe &quot;Azul&quot;", institutional)

    def test_preview_escapes_values_and_contains_named_pdf(self):
        csrf = self.login()
        response = self.preview(csrf, filename="..\\approved proposal.pdf",
                                mensagem="Contexto & <importante>")
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertIn("Ana &amp; Bia", body["html"])
        self.assertIn("Escola &lt;Beta&gt;", body["html"])
        self.assertIn("Contexto &amp; &lt;importante&gt;", body["html"])
        self.assertEqual(body["pdf_nome"], "approved_proposal.pdf")
        self.assertEqual(body["pdf_tamanho"], len(PDF))
        self.assertEqual(self.sent, [])

    def test_pdf_required_signature_extension_and_configured_size(self):
        csrf = self.login()
        missing = self.client.post("/api/preview", data={
            "template": "proposta", "destinatario": "direcao@example.com",
            "responsavel": "Ana", "assunto": "Proposta",
        }, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(self.preview(csrf, pdf=b"not-a-pdf").status_code, 400)
        self.assertEqual(self.preview(csrf, pdf=b"%PDF-1.4\ntruncated").status_code, 400)
        self.assertEqual(self.preview(csrf, filename="document.txt").status_code, 400)
        self.app.config["PDF_MAX_BYTES"] = 1024
        oversized = b"%PDF-1.4\n" + b"x" * 1010 + b"%%EOF\n"
        self.assertGreater(len(oversized), 1024)
        self.assertEqual(self.preview(csrf, pdf=oversized).status_code, 400)

    def test_environment_pdf_limit_and_proxy_configuration(self):
        with patch.dict(os.environ, {"CENTRAL_PDF_MAX_BYTES": "4096",
                                    "CENTRAL_TRUSTED_PROXY_HOPS": "1"}):
            app = create_app(testing=True)
        self.assertEqual(app.config["PDF_MAX_BYTES"], 4096)
        with patch.dict(os.environ, {"CENTRAL_PDF_MAX_BYTES": "1"}):
            with self.assertRaises(RuntimeError):
                create_app(testing=True)
        with patch.dict(os.environ, {"CENTRAL_TRUSTED_PROXY_HOPS": "-1"}):
            with self.assertRaises(RuntimeError):
                create_app(testing=True)

    def test_preview_session_scoped_and_expires(self):
        csrf = self.login()
        draft_id = self.preview(csrf).get_json()["draft_id"]
        other = self.app.test_client()
        other.environ_base["HTTP_HOST"] = "127.0.0.1:8765"
        other_csrf = self.login(other)
        self.assertEqual(self.send(other_csrf, draft_id, client=other).status_code, 409)
        draft = self.app.extensions["central_state"]["drafts"][draft_id]
        draft["expires"] = time.time() - 1
        self.assertEqual(self.send(csrf, draft_id).status_code, 409)

    def test_send_confirmation_mime_alternatives_and_exactly_once(self):
        csrf = self.login()
        draft_id = self.preview(csrf, mensagem="Acompanhe a reunião na sexta.").get_json()["draft_id"]
        self.assertEqual(self.send(csrf, draft_id, confirm="NAO").status_code, 400)
        response = self.send(csrf, draft_id)
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["status"], "aceito_pelo_smtp")
        self.assertEqual(len(self.sent), 1)
        message, user, password = self.sent[0]
        self.assertEqual(message["To"], "direcao@example.com")
        self.assertEqual(user, "comercial@example.com")
        self.assertEqual(password, "dummy-nonprod")
        self.assertIn("Acompanhe a reunião na sexta.", message.get_body(preferencelist=("plain",)).get_content())
        html_part = message.get_body(preferencelist=("html",))
        self.assertEqual(html_part.get_content_type(), "text/html")
        self.assertIn("Acompanhe a reunião na sexta.", html_part.get_content())
        attachments = list(message.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_content_type(), "application/pdf")
        self.assertEqual(attachments[0].get_filename(), "proposta.pdf")
        self.assertEqual(attachments[0].get_content(), PDF)
        self.assertIn("não garante a entrega", response.get_json()["message"])
        self.assertEqual(self.send(csrf, draft_id).status_code, 409)
        self.assertEqual(len(self.sent), 1)

    def test_concurrent_duplicate_send_is_consumed_once(self):
        csrf = self.login()
        draft_id = self.preview(csrf).get_json()["draft_id"]
        entered = threading.Event()
        release = threading.Event()

        def blocking_fake(*args):
            self.sent.append(args)
            entered.set()
            self.assertTrue(release.wait(3))

        self.app.config["SEND_MAIL"] = blocking_fake
        second_client = self.app.test_client()
        second_client.environ_base["HTTP_HOST"] = "127.0.0.1:8765"
        original_cookie = self.client.get_cookie("central_session", domain="127.0.0.1")
        second_client.set_cookie("central_session", original_cookie.value,
                                 domain="127.0.0.1")
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(self.send, csrf, draft_id)
            self.assertTrue(entered.wait(2))
            second = self.send(csrf, draft_id, client=second_client)
            release.set()
            first_response = first.result(timeout=3)
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(len(self.sent), 1)

    def test_smtp_auth_network_failure_and_missing_configuration(self):
        csrf = self.login()
        draft_id = self.preview(csrf).get_json()["draft_id"]
        self.app.config["SEND_MAIL"] = lambda *_: (_ for _ in ()).throw(
            smtplib.SMTPAuthenticationError(535, b"private server detail"))
        auth_failure = self.send(csrf, draft_id)
        self.assertEqual(auth_failure.status_code, 502)
        self.assertIn("autenticação", auth_failure.get_json()["error"].lower())
        self.assertNotIn("private server detail", auth_failure.get_json()["error"])

        draft_id = self.preview(csrf).get_json()["draft_id"]
        self.app.config["SEND_MAIL"] = lambda *_: (_ for _ in ()).throw(TimeoutError())
        network_failure = self.send(csrf, draft_id)
        self.assertEqual(network_failure.status_code, 502)
        self.assertIn("conexão", network_failure.get_json()["error"].lower())

        draft_id = self.preview(csrf).get_json()["draft_id"]
        with patch.dict(os.environ, {"LARK_SMTP_USER": "", "LARK_SMTP_APP_PASSWORD": ""}):
            missing_config = self.send(csrf, draft_id)
        self.assertEqual(missing_config.status_code, 503)
        self.app.config["SEND_MAIL"] = lambda *args: self.sent.append(args)
        self.assertEqual(self.send(csrf, draft_id).status_code, 200)

    def test_history_is_visible_and_isolated_per_session(self):
        csrf = self.login()
        draft_id = self.preview(csrf).get_json()["draft_id"]
        self.assertEqual(self.send(csrf, draft_id).status_code, 200)
        page = self.client.get("/")
        self.assertIn(b"Aceito pelo SMTP", page.data)
        other = self.app.test_client()
        other.environ_base["HTTP_HOST"] = "127.0.0.1:8765"
        self.login(other)
        other_page = other.get("/")
        self.assertIn("Nenhuma tentativa de envio registrada".encode(), other_page.data)
        self.assertNotIn(b"Aceito pelo SMTP", other_page.data)

    def test_health_check_is_minimal(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), "ok")


if __name__ == "__main__":
    unittest.main()
