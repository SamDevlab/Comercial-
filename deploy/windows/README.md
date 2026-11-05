# Execução local no Windows

Este runner usa Waitress, escuta somente em `127.0.0.1:8765` e fica no primeiro plano. Feche com `Ctrl+C`; ele não instala serviço nem inicia com o Windows. Não depende de Docker.

## Preparar uma vez

Use Python 3.12 e execute a partir da raiz do repositório:

```powershell
py -3.12 -m venv .venv
uv pip install --python .venv\Scripts\python.exe -r deploy\requirements-windows.txt
```

Se `uv` não estiver instalado, use `.\.venv\Scripts\python.exe -m pip install -r deploy\requirements-windows.txt`. Se o venv ainda não tiver pip, rode `.\.venv\Scripts\python.exe -m ensurepip --upgrade` antes.

Crie a senha e o segredo localmente, uma única vez:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\windows\initialize-local.ps1
```

O inicializador grava `central-comercial.env` e `admin-password.txt` em `%LOCALAPPDATA%\CentralComercial`, com ACL para o usuário atual, SYSTEM e Administradores locais. O valor da senha não é impresso. Guarde-a em um gerenciador de senhas autorizado e proteja a conta Windows; não copie esses arquivos para o repositório, chat ou logs. O inicializador recusa sobrescrever a pasta se ela já existir.

## Iniciar e conferir

```powershell
.\deploy\windows\run-local.ps1
```

Em outro terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/healthz
```

Abra `http://127.0.0.1:8765/login` no navegador local. O painel permite validar login, upload, prévia, histórico temporário e logout sem configurar SMTP. Teste apenas documentos autorizados. Sem as duas variáveis Lark, o envio e a autenticação SMTP permanecem indisponíveis. O PDF fica em memória e desaparece quando o rascunho expira, a sessão termina ou o processo reinicia.

O script não abre portas na rede local: o servidor recusa qualquer bind além de `127.0.0.1`. Não use o servidor de desenvolvimento Flask para acesso remoto.

## Lark Mail

O proprietário deve primeiro solicitar ao administrador do Lark a habilitação de clientes de e-mail externos e gerar uma senha dedicada no aplicativo Lark Mail. Depois, edite o arquivo `central-comercial.env` protegido e preencha `LARK_SMTP_USER` e `LARK_SMTP_APP_PASSWORD`; nunca passe os valores na linha de comando e não os salve no Git. Reinicie o processo local para carregar alterações. O botão “Testar autenticação sem enviar” só autentica em `smtp.larksuite.com:465` por SSL; esta campanha não executou autenticação real nem enviou mensagem.

## Tunnel e Access — preparação, ainda sem publicar

`../cloudflared/config.example.yml` é um modelo com UUID zerado e hostname reservado `central.example.com`; ele não autentica nem publica nada. Nenhuma zona foi verificada nesta máquina: `cloudflared` está instalado, mas não há `cert.pem`, configuração ou sessão da conta. Não execute `cloudflared login`, `tunnel create`, `route dns`, nem inicie um Tunnel antes de o proprietário fornecer a zona aprovada e autorizar os recursos exatos.

Proposta, sem provisionamento feito:

- Tunnel dedicado `central-comercial-local-v4`, com credencial protegida em `%USERPROFILE%\.cloudflared` e ACL do usuário atual.
- Hostname exclusivo `central-comercial.<zona-aprovada>` apontado somente para `http://127.0.0.1:8765`.
- Aplicação self-hosted do Cloudflare Access chamada `Central Comercial TecEscola`, com política Allow para o e-mail exato do proprietário e acesso negado por padrão. O Access deve estar ativo antes de tornar o hostname alcançável.
- Rota de fallback `http_status:404`; sem Quick Tunnel, sem outras portas e sem mudanças nos DNS/Workers existentes.

Após aprovação e criação desses recursos, preencher o hostname real em `config.yml` e definir no arquivo privado de ambiente `CENTRAL_PUBLIC_ORIGIN=https://<hostname-aprovado>` e `CENTRAL_TRUSTED_PROXY_HOPS=1`. Reinicie a aplicação e o Tunnel, então verifique Host, Origin, cookie Secure, CSRF e endereço do cliente pelo hostname HTTPS. Mantenha o app em loopback e não exponha o hostname antes de a política Access estar pronta. A configuração HTTPS foi simulada em teste Flask; não existe domínio HTTPS real validado.

## ChatGPT Work e PDFs

O Cloud Browser do Work executa remotamente e não recebe automaticamente arquivos, abas ou cookies do Windows local; a documentação do produto também informa que o navegador integrado não automatiza a seleção/upload de arquivos locais: [Browser](https://learn.chatgpt.com/docs/browser). Para usar um PDF do computador, a alternativa é abrir o painel no navegador local compatível com “Work locally”, usar a sessão local autorizada e selecionar manualmente o arquivo aprovado no seletor do navegador. A extensão de navegador pode exigir permissão para acessar URLs de arquivo local: [Extensão do navegador](https://learn.chatgpt.com/docs/chrome-extension).

O app mantém o PDF em memória para a prévia e não cria bucket ou link público. Acesso pelo Access, seleção de PDF e fluxo completo em uma sessão real do ChatGPT Work ainda precisam de um teste manual depois que o hostname estiver autorizado; não foram validados nesta campanha.
