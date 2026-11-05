# Runbook de implantação isolada

Estes passos destinam-se a uma VM Linux nova, dedicada e autorizada para a Central Comercial. Não os execute em `samdev-control-01`, na VPS de produção da TecEscola, nem em qualquer host que compartilhe serviços sem comprovação de isolamento, capacidade e autorização. Provisionamento de VM, cobrança, DNS, firewall/VPN e certificados dependem de autorização do proprietário.

## Pré-requisitos do host

- Ubuntu 24.04 LTS ou distribuição equivalente com Python 3.12, systemd e Nginx.
- Domínio autorizado com certificado TLS válido já emitido; este runbook não altera DNS nem emite certificado.
- Acesso privado ao painel configurado por VPN, firewall ou controle de acesso previamente aprovado. HTTPS sozinho não protege o painel de visitantes da Internet.
- Acesso de leitura ao repositório GitHub e conta Lark Mail com uso de cliente externo habilitado pelo administrador da organização.

## Instalação

Execute no host dedicado, adaptando o domínio e usando um método de autenticação Git aprovado para o repositório. Não coloque tokens de GitHub em argumentos, no repositório ou no chat.

```bash
sudo apt-get update
sudo apt-get install --no-install-recommends git nginx python3.12-venv
sudo useradd --system --create-home --home-dir /var/lib/central-comercial --shell /usr/sbin/nologin central-comercial
sudo install -d -o central-comercial -g central-comercial /opt/central-comercial
sudo -u central-comercial git clone --branch feat/central-comercial-lark-v1 --single-branch https://github.com/SamDevlab/Comercial-.git /opt/central-comercial
sudo -u central-comercial python3.12 -m venv /opt/central-comercial/.venv
sudo -u central-comercial /opt/central-comercial/.venv/bin/python -m pip install --upgrade pip
sudo -u central-comercial /opt/central-comercial/.venv/bin/python -m pip install -r /opt/central-comercial/deploy/requirements-linux.txt
```

Se o repositório for privado, autentique Git com o mecanismo seguro já aprovado no host antes de clonar. Não salve tokens no URL remoto.

## Segredos e acesso

Crie o arquivo privado de ambiente e não o adicione ao Git:

```bash
sudo install -d -o root -g central-comercial -m 0750 /etc/central-comercial
sudo install -o root -g central-comercial -m 0640 /opt/central-comercial/deploy/central-comercial.env.example /etc/central-comercial/central-comercial.env
sudo -u central-comercial /opt/central-comercial/.venv/bin/python -m central_comercial hash-password
sudo -u central-comercial /opt/central-comercial/.venv/bin/python -m central_comercial generate-secret
sudoedit /etc/central-comercial/central-comercial.env
```

Copie o hash e o segredo gerados diretamente para o arquivo editado. Defina `CENTRAL_PUBLIC_ORIGIN` como a origem HTTPS aprovada, sem caminho; mantenha `CENTRAL_BIND=127.0.0.1`, `CENTRAL_PORT=8765`, `CENTRAL_TRUSTED_PROXY_HOPS=1` e o limite PDF alinhado com Nginx. Insira `LARK_SMTP_USER` e `LARK_SMTP_APP_PASSWORD` somente aqui ou no gerenciador de segredos autorizado.

O proprietário da conta deve habilitar o acesso por cliente externo nas configurações administrativas do Lark e gerar uma senha dedicada no aplicativo desktop. O botão “Testar autenticação sem enviar” só valida login SMTP; não envia e-mail. A conta e a senha dedicada nunca devem ser inseridas no navegador, Git ou chat.

## Nginx, TLS e serviço

Edite `deploy/nginx/central-comercial.conf`: substitua o domínio de exemplo e aponte para os caminhos do certificado aprovado. O limite de 9 MiB aceita o PDF padrão de 8 MiB com folga para multipart. Se alterar `CENTRAL_PDF_MAX_BYTES`, atualize `client_max_body_size` também.

```bash
sudo install -m 0644 /opt/central-comercial/deploy/nginx/central-comercial.conf /etc/nginx/sites-available/central-comercial
sudo ln -s /etc/nginx/sites-available/central-comercial /etc/nginx/sites-enabled/central-comercial
sudo nginx -t
sudo install -m 0644 /opt/central-comercial/deploy/systemd/central-comercial.service /etc/systemd/system/central-comercial.service
sudo systemctl daemon-reload
sudo systemctl enable --now central-comercial
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

O Nginx deve ser o único caminho de entrada; a aplicação escuta apenas em loopback. Preserve `Host`, encaminhe `X-Forwarded-For` somente através do proxy controlado e não confie em cabeçalhos encaminhados de acesso direto. Restrinja a rede do host a VPN ou outro controle privado aprovado antes de habilitar acesso externo.

## Verificação e operação

```bash
sudo systemctl is-active central-comercial
sudo systemctl status central-comercial --no-pager
curl --fail --silent --show-error https://central.example.com/healthz
```

Confira o certificado e os cookies HTTPS; entre no painel, gere prévias para os dois modelos, confira os dados, teste o PDF e valide o logout. O botão SMTP testa a autenticação sem enviar. O envio requer autenticação validada nos últimos 15 minutos, uma nova prévia e confirmação explícita. Só execute envio real após autorização específica para uma conta e destinatário de teste.

Gunicorn fica em um worker porque sessões, rascunhos, idempotência e histórico são em memória. Reiniciar ou atualizar o serviço encerra sessões e descarta rascunhos/histórico temporários. Não escale horizontalmente sem migrar o estado compartilhado.

Logs de acesso do Nginx estão desabilitados. O formato do Gunicorn registra método, caminho e status, sem IP do cliente, query string ou corpo. Falhas SMTP são registradas sem resposta privada do servidor.

## Limite desta campanha

Os manifests foram revisados e o workflow instala `deploy/requirements-linux.txt`, inicia um Gunicorn de um worker em runner GitHub efêmero e valida `/healthz`. Esse smoke test não instala systemd/Nginx, não valida certificado, DNS, rede ou HTTPS do alvo, e não representa um deploy. Nenhum arquivo deste diretório foi aplicado a servidor nesta campanha.
