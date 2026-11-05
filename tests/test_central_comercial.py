import io
import os
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash
from central_comercial import create_app, valid_email

ORIGIN = "http://127.0.0.1:8765"
PASSWORD = "test-password-not-for-production"
PDF = b"%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF\n"


class CentralTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "CENTRAL_PUBLIC_ORIGIN": ORIGIN,
            "CENTRAL_ADMIN_PASSWORD_HASH": generate_password_hash(PASSWORD),
            "CENTRAL_SESSION_SECRET": "testing-secret-123456789012345678901234",
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
        r = client.post("/login", data={"password": PASSWORD},
                        headers={"Origin": ORIGIN})
        self.assertEqual(r.status_code, 302)
        self.assertIn("HttpOnly", r.headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", r.headers["Set-Cookie"])
        state = self.app.extensions["central_state"]["sessions"]
        return next(reversed(state.values()))["csrf"]

    def preview(self, csrf, *, client=None, pdf=PDF, email="direcao@example.com"):
        return (client or self.client).post("/api/preview", data={
            "template": "proposta",
            "destinatario": email,
            "responsavel": "Ana & Bia",
            "instituicao": "Escola <Beta>",
            "consultor": "Equipe",
            "assunto": "Proposta Escola Beta",
            "pdf": (io.BytesIO(pdf), "proposta.pdf"),
        }, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})

    def send(self, csrf, draft, *, client=None, confirm="ENVIAR"):
        return (client or self.client).post("/api/send",
            json={"draft_id": draft, "confirmacao": confirm},
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})

    def test_login_required(self):
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.post("/api/preview").status_code, 403)

    def test_wrong_password_rate_limit(self):
        for _ in range(6):
            r = self.client.post("/login", data={"password": "wrong"},
                                 headers={"Origin": ORIGIN})
            self.assertEqual(r.status_code, 401)
        self.assertEqual(self.client.post("/login", data={"password": PASSWORD},
                                         headers={"Origin": ORIGIN}).status_code, 429)

    def test_origin_csrf_and_host_protection(self):
        csrf = self.login()
        self.assertEqual(self.client.post("/api/preview").status_code, 403)
        self.assertEqual(self.client.post("/api/preview",
            headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.get("/", headers={"Host": "evil.example"}).status_code, 400)
        self.assertEqual(self.client.post("/api/preview", headers={"Origin": ORIGIN}).status_code, 403)

    def test_preview_escapes_values_and_never_sends(self):
        csrf = self.login()
        r = self.preview(csrf)
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertIn("Ana &amp; Bia", r.get_json()["html"])
        self.assertIn("Escola &lt;Beta&gt;", r.get_json()["html"])
        self.assertIn("A proposta está anexada", r.get_json()["html"])
        self.assertEqual(self.sent, [])

    def test_sends_exactly_once_with_pdf(self):
        csrf = self.login()
        draft = self.preview(csrf).get_json()["draft_id"]
        self.assertEqual(self.send(csrf, draft, confirm="NAO").status_code, 400)
        r = self.send(csrf, draft)
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(r.get_json()["status"], "aceito_pelo_smtp")
        self.assertEqual(len(self.sent), 1)
        msg, user, password = self.sent[0]
        self.assertEqual(msg["To"], "direcao@example.com")
        self.assertEqual(user, "comercial@example.com")
        self.assertEqual(list(msg.iter_attachments())[0].get_content(), PDF)
        self.assertEqual(self.send(csrf, draft).status_code, 409)
        self.assertEqual(len(self.sent), 1)

    def test_draft_is_session_scoped(self):
        csrf = self.login()
        draft = self.preview(csrf).get_json()["draft_id"]
        other = self.app.test_client()
        other.environ_base["HTTP_HOST"] = "127.0.0.1:8765"
        other_csrf = self.login(other)
        self.assertEqual(self.send(other_csrf, draft, client=other).status_code, 409)

    def test_pdf_and_email_checks(self):
        csrf = self.login()
        self.assertEqual(self.preview(csrf, pdf=b"not-a-pdf").status_code, 400)
        self.assertEqual(self.preview(csrf, email="a@example.com,b@example.com").status_code, 400)
        self.assertEqual(self.preview(csrf, pdf=b"%PDF-" + b"0" * (8 * 1024 * 1024)).status_code, 400)
        self.assertFalse(valid_email("A <a@example.com>"))
        self.assertTrue(valid_email("a@example.com"))

    def test_no_cache_no_embedding(self):
        r = self.client.get("/login")
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        self.assertIn("no-store", r.headers["Cache-Control"])
        self.assertIn("frame-ancestors 'none'", r.headers["Content-Security-Policy"])

    def test_logout_revokes_session(self):
        csrf = self.login()
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.post("/logout",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}).status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 302)


if __name__ == "__main__":
    unittest.main()
