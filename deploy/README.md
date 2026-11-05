# Modelos de implantação isolada

Esses arquivos são referências para uma nova instância Linux dedicada. Não foram instalados, habilitados nem aplicados em servidor nesta campanha.

1. Crie um usuário de sistema `central-comercial` e um diretório isolado `/opt/central-comercial` contendo apenas este repositório/branch.
2. Crie um ambiente virtual e instale `python3 -m pip install -r requirements.txt -r deploy/requirements-linux.txt`.
3. Copie `deploy/central-comercial.env.example` para `/etc/central-comercial/central-comercial.env`. Gere hash e segredo localmente; insira também as credenciais Lark dedicadas no gerenciador de segredos/arquivo protegido (permissão `0600`). Nunca comite esse arquivo.
4. Revise `deploy/nginx/central-comercial.conf`, configure um certificado TLS válido e restrinja o acesso ao host por firewall/VPN ou controle privado já aprovado. HTTPS sozinho não restringe quem acessa o login.
5. Instale `deploy/systemd/central-comercial.service` em `/etc/systemd/system/`, execute `systemctl daemon-reload`, habilite e inicie somente após confirmar que a instância está isolada.
6. Valide `/healthz`, login, cookies seguros, prévia, PDF e controles acessíveis. No painel, execute “Testar autenticação sem enviar”: esse comando só abre SMTP SSL e valida a senha dedicada. O envio só fica habilitado após autenticação validada recente, e ainda exige prévia e confirmação. Use o SMTP simulado em testes até existir autorização explícita para uma conta/destinatário de teste.

O Gunicorn fica em um único worker porque sessões, rascunhos, idempotência e histórico são em memória. O proxy deve preservar `Host` e ser o único caminho de entrada ao serviço. O Nginx recebe `X-Forwarded-For`; por isso o exemplo define `CENTRAL_TRUSTED_PROXY_HOPS=1`.

Os logs de acesso do Nginx estão desabilitados. O formato do Gunicorn registra somente método, caminho e status, sem IP do cliente, query string ou dados do formulário. Falhas SMTP são registradas sem resposta privada do servidor.

O `client_max_body_size` do Nginx acompanha o limite padrão de 8 MiB mais folga de multipart. Se `CENTRAL_PDF_MAX_BYTES` mudar, atualize também o limite do Nginx.

Estado atual: `DEPLOY=BLOCKED` até existir ambiente de homologação privado, autorizado e isolado. Estes templates não autorizam modificar a VPS compartilhada nem aplicações, DNS ou Cloudflare existentes.
