# Central Comercial V5 — ativação Cloudflare autorizada

## Escopo aprovado

Acesso remoto para a Central Comercial, que permanece executando via Waitress no computador Windows em \`127.0.0.1:8765\`. A autorização do proprietário abrange exclusivamente os recursos abaixo:

| Recurso | Valor |
| --- | --- |
| Zona Cloudflare a verificar | \`wstecnologiaaplicada.com.br\` |
| Hostname reservado | \`central-comercial.wstecnologiaaplicada.com.br\` |
| Tunnel exclusivo | \`central-comercial-local-v4\` |
| Aplicação Access | \`Central Comercial TecEscola\` |
| Identidade permitida | \`comercial@wstecnologiaaplicada.com.br\` |
| Origem local | \`http://127.0.0.1:8765\` |
| Fallback | \`http_status:404\` |

**Autorizado não significa provisionado.** Este repositório não contém login, certificado, token da API Cloudflare, Tunnel ID ou credenciais reais. Até executar e comprovar a criação na conta apropriada, declarar \`TUNNEL=NOT_CREATED\`, \`ACCESS=NOT_CONFIGURED\` e \`DNS=NOT_CONFIGURED\`.

## Ordem obrigatória — evitar exposição pública

1. Confirmar no painel/API Cloudflare que a zona aprovada está **ativa na conta autenticada**. Inspecionar o nome DNS aprovado e verificar que não pertence a outra aplicação. **Não substituir DNS existente**, nem alterar outros hostnames, Workers, zonas, serviços ou regras.
2. Confirmar que é possível receber o método de autenticação Access no único e-mail permitido. Na conta Zero Trust correta, criar/validar uma aplicação **Self-hosted** com hostname exato; política **Allow** específica apenas para \`comercial@wstecnologiaaplicada.com.br\`, sem Allow Everyone, Bypass, Service Auth pública ou inclusão por domínio \`@wstecnologiaaplicada.com.br\`. Access deve proteger todas as rotas, inclusive \`/healthz\`. Confirmar o resultado da política **antes de publicar DNS**.
3. Inspecionar a lista de Tunnels. Criar o \`central-comercial-local-v4\` **somente se não existir**. Nunca apagar/recriar túnel com mesmo nome sem investigar propriedade e dependências. O login interativo do Cloudflare pode ser exigido; concluir no navegador do proprietário, sem copiar cookies/tokens para chat ou Git.
4. Criar localmente, fora do Git, um \`config.yml\` a partir de \`config.v5.approved.example.yml\` com UUID e caminho real do JSON de credenciais do Tunnel. Validar sintaxe com a versão de \`cloudflared\` instalada. Credenciais devem manter ACL restrita. A configuração deve conter **somente** o hostname aprovado, encaminhamento a loopback e fallback 404.
5. Somente após confirmar a política Access, e **se não houver registro DNS conflitante**, criar a rota DNS do túnel. Para Tunnel local gerenciado via CLI, o comando documentado é \`cloudflared tunnel route dns central-comercial-local-v4 central-comercial.wstecnologiaaplicada.com.br\`; requer \`cert.pem\` da conta autorizada.
6. No arquivo privado \`%LOCALAPPDATA%\CentralComercial\central-comercial.env\`, ajustar \`CENTRAL_PUBLIC_ORIGIN=https://central-comercial.wstecnologiaaplicada.com.br\` e revisar \`CENTRAL_TRUSTED_PROXY_HOPS=1\` somente se o cabeçalho for efetivamente originado de proxy confiável. **Não sobrescrever o hash, o segredo de sessão nem credenciais existentes**. Reiniciar o runtime local pelo método já documentado.
7. Iniciar exclusivamente esse Tunnel, com configuração validada. Nenhuma instalação automática como serviço Windows está autorizada nesta etapa; manter execução manual como na V4.
8. Testar de fora da sessão autenticada: as rotas \`/\`, \`/login\`, \`/healthz\` e \`/api/preview\` **não devem entregar a aplicação anônima diretamente**. Devem exigir Access. Validar login autorizado em \`comercial@wstecnologiaaplicada.com.br\` e verificar bloqueio de qualquer outro endereço. Em sessão autenticada, verificar login interno, PDF, prévia, CSRF, Host, Origin, cookie Secure, logout e responsividade. Falha nesses critérios exige desligar o Tunnel sem afetar outros recursos.
9. Nunca marcar envio SMTP real como concluído sem credenciais Lark válidas e autorização separada para um e-mail de teste. A autorização de Cloudflare **não autoriza disparar propostas**.

## Comandos de referência — somente após preflight e login autorizado

\`\`\`powershell
cloudflared tunnel login
cloudflared tunnel list
cloudflared tunnel create central-comercial-local-v4
cloudflared tunnel --config "CAMINHO-PRIVADO/config-v5.yml" ingress validate
# SOMENTE após verificar a aplicação Access e ausência de DNS conflitante:
cloudflared tunnel route dns central-comercial-local-v4 central-comercial.wstecnologiaaplicada.com.br
cloudflared tunnel --config "CAMINHO-PRIVADO/config-v5.yml" run central-comercial-local-v4
\`\`\`

Não executar \`tunnel create\` se já existir túnel com o nome. Não executar \`route dns\` antes de garantir Access. O \`cert.pem\` e JSON de credenciais devem permanecer no perfil protegido, não no repo.

## Como usar com ChatGPT Work

Após HTTPS+Access efetivamente válidos, o Work poderá tentar abrir a URL publicada, concluir autenticação autorizada e operar o painel por navegador. Isso **não foi testado**. O Cloud Browser não recebe automaticamente o PDF do Windows; para automatizar também o anexo, exigir escolha local pelo operador ou implementar posteriormente uma biblioteca privada de PDFs aprovados, com autenticação, expiração, não exposição pública e trilha de auditoria.

## Relatório pós-provisionamento

\`\`\`text
CAMPAIGN=TEC_COMERCIAL_LARK_CLOUDFLARE_ACTIVATION_V5
CLOUDFLARE_ZONE=ACTIVE|NOT_FOUND|NOT_VERIFIED
ACCESS_APP=CREATED|EXISTING_VERIFIED|BLOCKED
ACCESS_ALLOWED_EMAIL=VERIFIED|NOT_VERIFIED
TUNNEL=CREATED|EXISTING_VERIFIED|BLOCKED
DNS=CREATED|EXISTING_VERIFIED|BLOCKED
PUBLIC_HOSTNAME=https://central-comercial.wstecnologiaaplicada.com.br
HTTPS=PASS|FAIL|NOT_TESTED
UNAUTHENTICATED_ACCESS=BLOCKED|NOT_TESTED
AUTHENTICATED_ACCESS=PASS|FAIL|NOT_TESTED
LOCAL_RUNTIME=PASS|FAIL|NOT_TESTED
LARK_SMTP_AUTH=PASS|BLOCKED|NOT_TESTED
REAL_EMAIL_SENT=NO
CHATGPT_WORK_REAL_TEST=PASS|BLOCKED|NOT_TESTED
UNRELATED_SERVICES_CHANGED=NO
RESULT=COMPLETE|PARTIAL|BLOCKED
\`\`\`

### Documentação oficial

- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/
- https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/
- https://developers.cloudflare.com/tunnel/concepts/routing/
