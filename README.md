# Central Comercial — WS Soluções / Tec Escola

Painel privado para enviar propostas da Tec Escola pelo Lark Mail, reutilizando os modelos HTML que já estavam neste repositório, sem copiar HTML no editor do e-mail.

## O que faz

- Apresentação institucional e proposta comercial com personalização do responsável, instituição, consultor e assunto.
- Anexo PDF obrigatório (máximo 8 MB), pois os modelos existentes dizem que existe um anexo.
- Prévia do HTML em iframe isolado, sem executar scripts.
- Confirmação humana antes de cada envio; prévia expira em 10 minutos e o rascunho não pode ser reutilizado.
- Autenticação, proteção CSRF/origem, limitação de tentativas e isolamento entre sessões.
- Envio SMTP SSL com certificado verificado. O aceite pelo SMTP não garante a entrega.

O enviador antigo por terminal (enviar-email-lark.py e enviar-email-lark.cmd) e os dois modelos HTML originais foram preservados.

## Testar localmente (não acessa produção)

Requer Python 3.12 ou superior. Na raiz do repositório:

    python -m venv .venv
    python -m pip install -r requirements.txt
    python -m central_comercial hash-password
    python -m central_comercial generate-secret

Configure estas variáveis no ambiente privado do seu computador. **Não salve valores reais no GitHub nem cole senhas no ChatGPT.**

| Variável | Finalidade |
| --- | --- |
| CENTRAL_ADMIN_PASSWORD_HASH | Hash gerado pelo comando hash-password |
| CENTRAL_SESSION_SECRET | Segredo aleatório gerado pelo comando generate-secret |
| CENTRAL_PUBLIC_ORIGIN | http://127.0.0.1:8765 em desenvolvimento |
| CENTRAL_BIND | 127.0.0.1 (padrão, sem acesso externo) |
| CENTRAL_PORT | 8765 (padrão) |
| LARK_SMTP_USER | Endereço corporativo do Lark |
| LARK_SMTP_APP_PASSWORD | Senha dedicada de aplicativo do Lark |

Depois execute:

    python -m central_comercial

Acesse http://127.0.0.1:8765/login. A prévia funciona sem credenciais SMTP, mas o envio fica bloqueado enquanto o Lark não estiver configurado.

Para gerar senha dedicada no Lark desktop: Perfil > Configurações > E-mail > Login de clientes de e-mail de terceiros > Gerar senha dedicada (o administrador talvez precise habilitar). Documentação:
https://www.larksuite.com/hc/en-US/articles/378111206512-log-in-to-lark-mail-through-a-third-party-email-client

## Operar pelo ChatGPT Work (após uma implantação autorizada)

Esta versão oferece um fluxo de navegador, não um conector Lark nativo nem uma API pública de disparo. Após a publicação em um endereço HTTPS privado, o ChatGPT Work poderá abrir a central autenticada, preencher os dados do cliente, selecionar o PDF já autorizado, conferir a prévia e solicitar confirmação antes do envio. A senha SMTP fica no servidor.

Exemplo de comando no Work: "Abra minha Central Comercial e prepare uma proposta para Maria, do Colégio Exemplo, no e-mail informado; anexe o PDF aprovado e mostre a prévia antes de enviar."

**Nenhum deployment ou acesso à VPS foi executado nesta campanha. Nenhum e-mail real foi enviado.**

## VPS (somente etapa futura, não executada)

- Exigir HTTPS, proxy reverso, autenticação adicional se possível e origem pública configurada exatamente como a URL do navegador.
- Executar apenas um processo/worker do aplicativo, escutando em 127.0.0.1 (sessões e prévias ficam em memória).
- Em Linux, por exemplo, instalar Gunicorn separadamente e usar: gunicorn -w 1 -b 127.0.0.1:8765 'central_comercial:create_app()'.
- Preservar o header Host no proxy HTTPS; limitar upload e usar TLS válido.
- Guardar senhas com permissões restritas ou gerenciador de segredos, nunca em commits ou logs.
- Não expor o servidor de desenvolvimento do Flask diretamente à Internet.

## Limites da versão 1

Rascunhos e sessões são temporários e desaparecem no reinício; não há histórico persistente, CRM, confirmação de leitura/entrega nem envio em massa. Auditoria mínima somente com horário, modelo e status em memória. Um destinatário por mensagem e limite de 20 tentativas de envio por hora. A prévia pode renderizar de maneira diferente em outros clientes de e-mail.

## Testes (SMTP simulado, sem rede)

    python -m unittest discover -s tests -v

O workflow GitHub Actions testa autenticação, sessão, CSRF, validação do PDF, escape do HTML, proteção contra reenvio e isolamento. Nenhum teste usa credenciais ou envia mensagens reais.

Veja também COMO-ENVIAR-PELO-LARK.md para a forma antiga de enviar pelo terminal Windows.
