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

Requer Python 3.12 ou superior. Para operação local no Windows, use Waitress e os arquivos de segredo protegidos pelo ACL do usuário; o passo a passo está em [`deploy/windows/README.md`](deploy/windows/README.md). Não é necessário Docker:

```powershell
py -3.12 -m venv .venv
uv pip install --python .venv\Scripts\python.exe -r deploy\requirements-windows.txt
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\windows\initialize-local.ps1
.\deploy\windows\run-local.ps1
```

O comando usa `uv`; se ele não estiver instalado, veja a alternativa com pip no runbook. O runner escuta apenas em `127.0.0.1:8765`; abra <http://127.0.0.1:8765/login>. O inicializador cria hash scrypt, segredo de sessão e senha administrativa aleatórios em `%LOCALAPPDATA%\CentralComercial`, com ACL restrita. Não imprime a senha nem instala início automático. Sem variáveis Lark, prévias funcionam e envio fica indisponível. Para desenvolvimento, `python -m central_comercial` continua disponível, mas não use o servidor Flask de desenvolvimento como serviço remoto.

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

O transporte usa SMTP SSL com validação normal de certificado, servidor `smtp.larksuite.com` e porta `465`. A documentação oficial do Lark exige habilitação administrativa para clientes externos e uma senha dedicada gerada no aplicativo desktop: [Login no Lark Mail por cliente de e-mail externo](https://www.larksuite.com/hc/en-US/articles/378111206512-log-in-to-lark-mail-through-a-third-party-email-client).

O botão “Testar autenticação sem enviar” abre uma conexão SSL e autentica sem criar uma mensagem. A rota exige sessão, Origin e token CSRF, limita tentativas a uma por minuto e não retorna respostas SMTP privadas. Uma autenticação válida permite envio por 15 minutos; o painel não armazena a senha no navegador. O envio continua exigindo prévia e confirmação explícita. Uma resposta de aceitação SMTP não confirma entrega.

## Segurança e operação

- Uma conta administrativa protegida por hash scrypt; cookies assinados, `HttpOnly`, `SameSite=Strict` e `Secure` quando a origem é HTTPS.
- Sessões expiram em 8 horas; rascunhos em 10 minutos. Logout revoga a sessão e apaga seus rascunhos.
- CSRF exige `Origin` exata e token no formulário autenticado. `Host` é conferido, headers de segurança e CSP são definidos.
- Bloqueio de tentativa de login por IP, limite de 20 tentativas de envio por hora, autenticação SMTP obrigatória antes do envio e reserva atômica para impedir reenvio concorrente do mesmo rascunho.
- PDF é limitado, validado por cabeçalho e marcador final, tem nome sanitizado e fica somente em memória; não é extraído nem executado.
- Histórico temporário da sessão mostra data, modelo e resultado, sem guardar destinatário, assunto, corpo ou credenciais. Ele desaparece ao sair ou reiniciar.
- Estado de sessão, rascunho e limite de envio é em memória. Use uma instância/worker da aplicação; não escale horizontalmente sem migrar esse estado para armazenamento compartilhado.
- Falhas de autenticação SMTP e de conexão recebem mensagens separadas, sem detalhes da resposta do servidor. O log de acesso do Nginx fica desabilitado e o formato de acesso do Gunicorn omite IP, query string e corpo. Uma tentativa de envio consome o rascunho antes da conexão para evitar duplicidade quando a resposta SMTP for incerta; uma nova tentativa exige nova prévia.

Em proxy reverso, preserve `Host`, encaminhe `X-Forwarded-For` de um proxy confiável e configure `CENTRAL_TRUSTED_PROXY_HOPS=1`. O app deve escutar somente em loopback. Não habilite confiança em cabeçalhos encaminhados de tráfego direto da Internet.

## Implantação Linux isolada

Os arquivos-base de systemd, Nginx e ambiente estão em [`deploy/`](deploy/). Eles são modelos, não foram aplicados a nenhuma VPS. O serviço usa usuário dedicado, Gunicorn com um worker e escuta em loopback; o Nginx exige certificado TLS já provisionado. Ajuste domínio, caminho, limite de upload e políticas de acesso antes de instalar. O workflow valida a instalação do manifesto Linux e inicia o Gunicorn em um runner GitHub efêmero para consultar `/healthz`; isso não é um deploy nem valida o certificado ou proxy de uma hospedagem real.

Situação desta campanha: `WINDOWS_LOCAL=AVAILABLE`; `PUBLIC_TUNNEL=BLOCKED_PENDING_CLOUDFLARE_AUTHORIZATION`. O runtime local está disponível em loopback. Não há zona ou identidade Cloudflare autorizada demonstrável nesta sessão, nem ambiente de homologação/VPS. Nenhuma produção, DNS, Cloudflare ou serviço foi alterado. Não exponha o painel antes de configurar HTTPS, Access, hash de senha, segredo e credenciais SMTP.

## Windows local e Cloudflare Tunnel

O runtime Windows usa Waitress em loopback e não cria serviço. O modelo de Tunnel e a proposta de Access estão em [`deploy/windows/README.md`](deploy/windows/README.md) e [`deploy/cloudflared/config.example.yml`](deploy/cloudflared/config.example.yml). Cloudflare não está configurado: não há sessão, certificado ou zona verificada. O hostname, túnel, política Access e registro DNS precisam de autorização explícita do proprietário; não há mudanças de DNS ou Workers.

## ChatGPT Work

O painel tem labels, controles nativos, estados acessíveis, confirmação no navegador e seletores `data-testid` estáveis. Não existe conector nativo Lark/ChatGPT nem atalho público de envio. O Cloud Browser do ChatGPT Work executa remotamente e não acessa arquivos locais do Windows; o navegador integrado não automatiza a seleção/upload de arquivo local. Para PDF local, use “Work locally” no app de desktop quando disponível, ou um navegador local compatível com a extensão e selecione o arquivo aprovado manualmente. Consulte [Browser](https://learn.chatgpt.com/docs/browser), [Escolher trabalho local ou na nuvem](https://learn.chatgpt.com/docs/use-chatgpt) e [Extensão do navegador](https://learn.chatgpt.com/docs/chrome-extension). A compatibilidade real com Cloudflare Access e o fluxo do Work não foram testados; veja [`deploy/windows/README.md`](deploy/windows/README.md).

## Testes

```powershell
python -m compileall -q central_comercial
python -m unittest discover -s tests -v
```

Os testes cobrem autenticação, logout e expiração, origem/Host/CSRF, cookies, isolamento, limites e validação de PDF, escape dos dois modelos, MIME, confirmação, reenvio concorrente, histórico, diagnóstico SMTP, expiração da autenticação e erros SMTP simulados. Nenhum teste usa credenciais reais ou envia e-mail. O workflow GitHub Actions roda compilação e a suíte em Python 3.12; também inicia Gunicorn com um worker em runner efêmero e testa o health check local.

Layout responsivo é implementado com breakpoints de tablet e celular; a conferência em navegador desktop/mobile deve ser feita após iniciar o servidor local.

## Limitações

Não há envio em massa, CRM, persistência, confirmação de leitura/entrega, verificação visual nos clientes Gmail/Outlook/Lark ou teste de SMTP real. A aparência da prévia do navegador pode diferir dos clientes de e-mail.
