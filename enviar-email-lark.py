#!/usr/bin/env python3
"""Envia os HTMLs Tec Escola via SMTP da propria conta Lark Mail.

Nenhuma senha e gravada; uso exige confirmacao de envio pelo operador.
"""
from __future__ import annotations

import getpass
import html
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELOS = {
    "1": ("apresentacao-institucional.html", "Conheça a Tec Escola"),
    "2": ("propostacomercial-pronta.html", "Sua proposta comercial Tec Escola está pronta"),
}


def entrada(mensagem: str, obrigatorio: bool = True) -> str:
    while True:
        valor = input(mensagem).strip()
        if valor or not obrigatorio:
            return valor
        print("Este campo é obrigatório.")


def email_valido(endereco: str) -> bool:
    return (parseaddr(endereco)[1] == endereco and
            re.fullmatch(r"[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+", endereco) is not None)


def pedir_email(mensagem: str) -> str:
    while True:
        valor = entrada(mensagem)
        if email_valido(valor):
            return valor
        print("Informe um único e-mail válido.")


def main() -> None:
    print("\n=== Tec Escola — envio de HTML pelo Lark Mail ===")
    print("1. Apresentação institucional\n2. Proposta comercial pronta")
    while (opcao := entrada("Escolha 1 ou 2: ")) not in MODELOS:
        print("Escolha inválida.")
    arquivo, assunto_padrao = MODELOS[opcao]
    modelo = ROOT / arquivo
    if not modelo.is_file():
        raise SystemExit(f"Arquivo não encontrado: {modelo}")

    remetente = pedir_email("Seu e-mail corporativo no Lark: ")
    destino = pedir_email("E-mail do destinatário: ")
    responsavel = entrada("Nome do responsável: ")
    instituicao = entrada("Nome da instituição (opcional): ", False) or "sua instituição"
    consultor = entrada("Nome do consultor (opcional): ", False) or "Equipe Comercial"
    assunto = entrada(f"Assunto [Enter = {assunto_padrao}]: ", False) or assunto_padrao
    while True:
        pdf = entrada("Caminho completo do PDF que será anexado: ").strip('"')
        anexo = Path(pdf).expanduser()
        if anexo.is_file() and anexo.suffix.lower() == ".pdf":
            break
        print("Informe um caminho existente de arquivo PDF (os modelos mencionam anexo).")

    codigo = modelo.read_text(encoding="utf-8")
    for marcador, valor in {
        "[Nome do responsável]": responsavel,
        "[Nome da instituição]": instituicao,
        "[Nome do consultor]": consultor,
    }.items():
        codigo = codigo.replace(marcador, html.escape(valor, quote=False))

    msg = EmailMessage()
    msg["From"] = formataddr(("Tec Escola", remetente))
    msg["To"] = destino
    msg["Subject"] = assunto
    msg.set_content(f"Olá, {responsavel}!\n\nSegue o material da Tec Escola em anexo.\n")
    msg.add_alternative(codigo, subtype="html", charset="utf-8")
    msg.add_attachment(anexo.read_bytes(), maintype="application", subtype="pdf", filename=anexo.name)

    print("\nConfira antes do envio:")
    for rotulo, valor in [
        ("Remetente", remetente), ("Destinatário", destino),
        ("Assunto", assunto), ("Modelo", arquivo), ("Anexo", anexo.name)
    ]:
        print(f"  {rotulo}: {valor}")
    if entrada("\nDigite ENVIAR para confirmar: ") != "ENVIAR":
        print("Envio cancelado.")
        return
    senha = getpass.getpass("Senha dedicada de aplicativo do Lark: ")
    if not senha:
        raise SystemExit("Senha não informada, envio cancelado.")
    try:
        with smtplib.SMTP_SSL("smtp.larksuite.com", 465, timeout=30,
                              context=ssl.create_default_context()) as smtp:
            smtp.login(remetente, senha)
            smtp.send_message(msg)
        print("Enviado ao servidor SMTP do Lark. Confirme o recebimento em uma conta de teste.")
    except (smtplib.SMTPException, OSError) as exc:
        raise SystemExit(f"Falha no SMTP do Lark: {exc}") from None
    finally:
        senha = None


if __name__ == "__main__":
    main()
