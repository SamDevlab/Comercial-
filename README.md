# Central Comercial — WS Soluções / Tec Escola

Painel privado para preparar propostas comerciais personalizadas e enviá-las pelo Lark Mail. Reutiliza os dois modelos HTML existentes; não depende de colar HTML no editor do Lark.

## Fluxo

1. Entre com a senha administrativa.
2. Escolha apresentação institucional ou proposta comercial e preencha responsável, instituição, destinatário, consultor, assunto e mensagem complementar opcional.
3. Anexe o PDF aprovado. O limite padrão é 8 MiB e pode ser configurado.
4. Gere e confira a prévia, incluindo destinatário, assunto e nome/tamanho do PDF.
5. Confirme no botão e na caixa do navegador. O servidor reserva o rascunho antes de falar com o SMTP e não o reutiliza.

O modelo HTML original é enviado como `text/html` dentro de uma mensagem MIME multipart com alternativa `text/plain` e o PDF anexado. Dados inseridos são escapados. Um destinatário por mensagem. O painel informa que a aceitação pelo SMTP não confirma entrega.

## Instalação local

Requer Python 3.12 ou superior. O exemplo abaixo usa PowerShell no Windows e não depende de Docker:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:CENTRAL_ADMIN_PASSWORD_HASH = python -m central_comercial hash-password
$env:CENTRAL_SESSION_SECRET = python -m central_comercial generate-secret
python -m central_comercial
```

Os comandos de senha pedem a senha sem exibi-la. Configure o SMTP só em ambiente privado, nunca em `.env.example`, Git ou logs. Para uso local, abra <http://127.0.0.1:8765/login>. Sem variáveis Lark, prévias funcionam e envio fica indisponível.

## Variáveis de ambiente

| Variável | Uso |
| --- | --- |
| `CENTRAL_ADMIN_PASSWORD_HASH` | Hash scrypt produzido por `python -m central_comercial hash-password` |
| `CENTRAL_SESSION_SECRET` | Segredo aleatório de pelo menos 32 caracteres |
| `CENTRAL_PUBLIC_ORIGIN` | Origem exata do navegador, por exemplo `https://central.exemplo.com.br` |
| `CENTRAL_BIND` / `CENTRAL_PORT` | Endereço e porta de escuta; padrão `127.0.0.1:8765` |
| `CENTRAL_PDF_MAX_BYTES` | Limite do PDF em bytes; padrão 8 MiB, mínimo 1 KiB e máximo 25 MiB |
| `CENTRAL_TRUSTED_PROXY_HOPS` | Saltos de proxy confiáveis usados para limitar tentativas por IP; padrão `0`, use `1` somente atrás de um proxy controlado |
| `LARK_SMTP_USER` | E-mail da conta Lark usada como remetente |
| `LARK_SMTP_APP_PASSWORD` | Senha dedicada para cliente de e-mail, somente no ambiente privado |

Veja `.env.example` para os nomes sem valores secretos. A aplicação não lê `.env` automaticamente: configure as variáveis no processo, em um arquivo de ambiente privado ou em um gerenciador de segredos.

## Lark SMTP

O transporte usa SMTP SSL com validação normal de certificado, timeout de 25 segundos, servidor `smtp.larksuite.com` e porta `465`. A documentação oficial do Lark exige habilitação administrativa para clientes externos e uma senha dedicada gerada no aplicativo desktop: [Login no Lark Mail por cliente de e-mail externo](https://www.larksuite.com/hc/en-US/articles/378111206512-log-in-to-lark-mail-through-a-third-party-email-client).

Não há teste automatizado que envie mensagem. Os testes substituem o transporte por uma função simulada. O status “Lark configurado” só confirma que as duas variáveis parecem presentes; não autentica a conta nem confirma entrega.

## Segurança e operação

- Uma conta administrativa protegida por hash scrypt; cookies assinados, `HttpOnly`, `SameSite=Strict` e `Secure` quando a origem é HTTPS.
- Sessões expiram em 8 horas; rascunhos em 10 minutos. Logout revoga a sessão e apaga seus rascunhos.
- CSRF exige `Origin` exata e token no formulário autenticado. `Host` é conferido, headers de segurança e CSP são definidos.
- Bloqueio de tentativa de login por IP, limite de 20 tentativas de envio por hora e reserva atômica para impedir reenvio concorrente do mesmo rascunho.
- PDF é limitado, validado por cabeçalho e marcador final, tem nome sanitizado e fica somente em memória; não é extraído nem executado.
- Histórico temporário da sessão mostra data, modelo e resultado, sem guardar destinatário, assunto, corpo ou credenciais. Ele desaparece ao sair ou reiniciar.
- Estado de sessão, rascunho e limite de envio é em memória. Use uma instância/worker da aplicação; não escale horizontalmente sem migrar esse estado para armazenamento compartilhado.
- Falhas de autenticação SMTP e de conexão recebem mensagens separadas. Uma tentativa consome o rascunho antes da conexão para evitar duplicidade quando a resposta SMTP for incerta; uma nova tentativa exige nova prévia.

Em proxy reverso, preserve `Host`, encaminhe `X-Forwarded-For` de um proxy confiável e configure `CENTRAL_TRUSTED_PROXY_HOPS=1`. O app deve escutar somente em loopback. Não habilite confiança em cabeçalhos encaminhados de tráfego direto da Internet.

## Implantação Linux isolada

Os arquivos-base de systemd, Nginx e ambiente estão em [`deploy/`](deploy/). Eles são modelos, não foram aplicados a nenhuma VPS. O serviço usa usuário dedicado, Gunicorn com um worker e escuta em loopback; o Nginx exige certificado TLS já provisionado. Ajuste domínio, caminho, limite de upload e políticas de acesso antes de instalar.

Situação desta campanha: `DEPLOY=BLOCKED`. Não há ambiente de homologação isolado, domínio autorizado ou acesso demonstrável à VPS nesta sessão. Nenhuma produção, DNS, Cloudflare ou serviço foi alterado. Não exponha o painel antes de configurar HTTPS, acesso privado (por exemplo VPN ou controle de acesso já autorizado), hash de senha, segredo e credenciais SMTP.

## ChatGPT Work

O painel tem labels, controles nativos, estados acessíveis e confirmação no navegador. Isso prepara uma automação por navegador após a implantação privada. Não existe conector nativo Lark/ChatGPT nem atalho público de envio. O teste específico com sessão real do ChatGPT Work depende de uma instância HTTPS autorizada e sessão autenticada; permanece pendente.

## Testes

```powershell
python -m compileall -q central_comercial
python -m unittest discover -s tests -v
```

Os testes cobrem autenticação, logout e expiração, origem/Host/CSRF, cookies, isolamento, limites e validação de PDF, escape dos modelos, MIME, confirmação, reenvio concorrente, histórico e erros SMTP simulados. Nenhum teste usa credenciais reais ou envia e-mail. O workflow GitHub Actions roda compilação e a mesma suíte em Python 3.12.

Layout responsivo é implementado com breakpoints de tablet e celular; a conferência em navegador desktop/mobile deve ser feita após iniciar o servidor local.

## Limitações

Não há envio em massa, CRM, persistência, confirmação de leitura/entrega, verificação visual nos clientes Gmail/Outlook/Lark ou teste de SMTP real. A aparência da prévia do navegador pode diferir dos clientes de e-mail.
