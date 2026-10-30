# Enviar modelos da Tec Escola pelo Lark sem colar o HTML

O envio via SMTP do Lark mantém o HTML como corpo de e-mail, evitando que o editor visual reescreva a formatação ao colar. Diferentes clientes de e-mail ainda podem renderizar o conteúdo de modo distinto.

## Preparar a conta

No **aplicativo Lark desktop**: Perfil > Configurações > E-mail > Login de clientes de e-mail de terceiros > Gerar senha dedicada. O administrador pode precisar habilitar essa função. Guarde a senha em segurança e não a coloque neste repositório.

Documentação oficial: https://www.larksuite.com/hc/en-US/articles/378111206512-log-in-to-lark-mail-through-a-third-party-email-client

## Enviar no Windows

1. Baixe o repositório completo (Code > Download ZIP) e extraia os arquivos.
2. Tenha Python 3 instalado.
3. Abra **enviar-email-lark.cmd** com dois cliques.
4. Escolha apresentação institucional ou proposta comercial.
5. Informe endereço Lark, destinatário, dados do cliente, assunto e o caminho do PDF anexo.
6. Revise as informações e digite **ENVIAR** para confirmar.
7. Informe a senha dedicada, gerada no Lark.

Use primeiro seu próprio endereço como destinatário e confira a renderização no celular.

## Segurança

- O script não salva nem publica a senha ou os dados informados.
- Nenhuma mensagem é enviada sem confirmação explícita.
- O PDF é obrigatório porque os dois HTMLs dizem que existe anexo.
- Não adicione senhas nem PDFs de clientes ao repositório público.
- A imagem da logo depende do endereço HTTPS contido no HTML.
- O acesso SMTP pode estar indisponível se a organização não permitir clientes externos.
- O envio por SMTP não garante visual idêntico em Gmail, Outlook, Apple Mail e outros aplicativos.
