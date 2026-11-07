# Migração DNS Cloudflare — V7

Data: 2026-11-05

## Escopo autorizado

Zona `wstecnologiaaplicada.com.br`, conta Cloudflare `Samusilvadev`, nameservers aprovados `ali.ns.cloudflare.com` e `apollo.ns.cloudflare.com`. O objetivo é migrar sem alterar serviços não relacionados.

## Etapa 1 — inventário e Lark: PASS

O painel autenticado do Registro.br, em modo avançado, exibiu sete registros. A zona Cloudflare da conta indicada pelo proprietário está no plano Free, permanece pendente de delegação e exibe `7 of 200` registros, todos DNS-only. A tabela de origem e a zona Cloudflare correspondem:

| Tipo | Nome | Dados conferidos |
| --- | --- | --- |
| MX | `@` | `mx1.larksuite.com`, prioridade 1 |
| MX | `@` | `mx2.larksuite.com`, prioridade 5 |
| MX | `@` | `mx3.larksuite.com`, prioridade 10 |
| TXT | `@` | SPF do Lark presente |
| TXT | `@` | Verificação do Lark presente; valor omitido |
| TXT | `_dmarc` | DMARC do Lark presente |
| TXT | `lark2610221127._domainkey` | DKIM do Lark presente; chave pública omitida |

As consultas DNS públicas também retornaram os três MX e os quatro TXT esperados. Não há A/AAAA/CNAME no domínio raiz ou em `www`. Nenhum destino de hospedagem foi inventado. Nenhum registro foi alterado nesta execução.

## DNSSEC observado antes da migração

Consultas diretas aos seis servidores autoritativos `.br` (`a.dns.br` a `f.dns.br`) retornaram o mesmo DS: tag `46835`, algoritmo `13`, digest type `2`, TTL `3600` segundos. Dois resolvedores públicos confirmaram a delegação atual para `b.sec.dns.br` e `c.sec.dns.br`.

Na tela autenticada do domínio, o Registro.br informa: “Você está utilizando os servidores DNS do Registro.br”. O formulário “Alterar servidores DNS” oferece campos para servidores e ação de adicionar DNSSEC, mas não apresenta ação de remoção isolada do DS.

## Etapa 2 — remover DS antigo: BLOCKED, nenhuma alteração

O DS antigo continua publicado nos seis servidores `.br`. O painel não fornece remoção independente enquanto a zona usa o DNS autoritativo do Registro.br. A documentação oficial informa que DNSSEC nos servidores DNS do próprio Registro.br é automático e não pode ser desativado isoladamente; sair desse serviço requer informar servidores DNS externos. Consulte [DNS e DNSSEC](https://registro.br/tecnologia/dnssec/dns-e-dnssec/) e [características técnicas do DNS do Registro.br](https://registro.br/tecnologia/caracteristicas-tecnicas/).

Como não foi possível remover o DS mantendo os nameservers atuais, não há instante comprovado de início da expiração do TTL. **Aguardamento de TTL não iniciado; cadeia DNSSEC antiga ainda publicada.** Não submeti o formulário de alteração de nameservers, pois isso violaria a ordem aprovada.

## Etapas seguintes — não executadas

| Etapa | Estado | Evidência |
| --- | --- | --- |
| Esperar expiração completa do TTL e comprovar remoção do DS | BLOQUEADA | O DS segue nos seis servidores `.br`, TTL observado 3600 s |
| Alterar nameservers para `ali.ns.cloudflare.com` e `apollo.ns.cloudflare.com` | NÃO EXECUTADA | Os resolvedores consultados continuam retornando `b.sec.dns.br` e `c.sec.dns.br` |
| Verificar propagação e Lark após delegação | NÃO EXECUTADA | Delegação não alterada |
| Ativar DNSSEC no Cloudflare e publicar novo DS | NÃO EXECUTADA | Zona ainda pendente |
| Ativar Tunnel e Access | NÃO EXECUTADA | Dependem da zona ativa; nenhum recurso foi criado nesta etapa |

## Proteção de serviços e estado final

Nenhuma alteração foi feita em nameservers, zona autoritativa, email, Email Routing, Workers, VPS, aplicações ou registros DNS. Não houve contratação, envio de email ou merge.

```text
INVENTORY=PASS
LARK_RECORDS=PRESERVED
OLD_DS=STILL_PUBLISHED_TTL_3600
DS_REMOVAL=BLOCKED_REGISTRO_BR_DNSSEC_AUTOMATIC
NAMESERVER_CHANGE=NOT_EXECUTED
CLOUDFLARE_ZONE=CREATED_PENDING_DELEGATION
DNSSEC_CLOUDFLARE=NOT_CONFIGURED
TUNNEL_ACCESS=NOT_CREATED
PRODUCTION_CHANGED=NO
```

## Atualização V8 — fluxo integrado autorizado, recibo pendente

Em 2026-11-05, o proprietário autorizou o fluxo integrado oficial do Registro.br. Antes do único envio, foram reconfirmados:

- Sete registros com correspondência exata entre a tabela autenticada do Registro.br e a zona Cloudflare (3 MX e 4 TXT), todos DNS-only na conta `Samusilvadev`.
- `ali.ns.cloudflare.com` e `apollo.ns.cloudflare.com` responderam diretamente com o SOA da zona e flag DNS `auth. answer` (`NOERROR`).
- A zona Cloudflare continuava pendente de delegação.

Os campos do Registro.br foram preenchidos somente com os dois nameservers aprovados. Após uma única confirmação, a página redirecionou para `registro.br/login/?session=required` em vez de apresentar recibo. Nenhum segundo envio foi feito.

As consultas técnicas subsequentes confirmaram que, em duas observações, o DS `46835` seguia publicado nos seis servidores `.br` com TTL de 3600 s, os resolvedores `1.1.1.1` e `8.8.8.8` ainda retornavam `b.sec.dns.br` e `c.sec.dns.br`, e os três MX do Lark continuavam resolvendo. Esse estado inicial é compatível com o atraso documentado do Registro.br, mas não comprova que o pedido foi aceito.

**Estado do envio: SUBMIT_ATTEMPTED_UNCONFIRMED.** A sessão do Registro.br expirou; é necessário reautenticar e conferir no painel se a solicitação integrada está pendente ou foi aceita. Não reenviar a alteração nem avançar DNSSEC/Tunnel/Access até essa confirmação. O TTL de espera e a transição da delegação ainda não podem ser considerados concluídos.

Após a reautenticação manual do proprietário, a página de administração ainda informa “Você está utilizando os servidores DNS do Registro.br”. O formulário de alteração abriu com os campos Server 1 e Server 2 vazios e não exibiu recibo nem status de solicitação pendente. Isso não prova se o envio anterior foi rejeitado ou ficou em processamento. Uma nova rodada DNS confirmou o DS `46835` nos seis servidores `.br`, os nameservers antigos em ambos os resolvedores consultados e os MX do Lark ainda resolvendo. A solicitação permanece inconclusiva e não foi reenviada.

```text
PRE_SUBMIT_INVENTORY=PASS_EXACT_7
PRE_SUBMIT_CLOUDFLARE_NS_AUTHORITY=PASS_BOTH
REGISTRO_BR_REQUEST=SUBMIT_ATTEMPTED_UNCONFIRMED
REGISTRO_BR_PANEL=REAUTHENTICATED_NO_RECEIPT_OR_PENDING_STATUS
OLD_DS=STILL_PUBLISHED_TTL_3600
PUBLIC_NS=STILL_REGISTRO_BR_AT_LAST_CHECK
LARK_MX=RESOLVING_AT_LAST_CHECK
RESUBMISSION=NO
DNSSEC_CLOUDFLARE=NOT_CONFIGURED
TUNNEL_ACCESS=NOT_CREATED
PUBLIC_DNS_CHANGE=NOT_SEEN_AT_LAST_CHECK
```

## V8 Recovery — consulta somente leitura

Snapshot DNS coletado em **2026-11-05 20:37:24 -03:00**. O painel autenticado do Registro.br ainda informa que o domínio utiliza o DNS do Registro.br; o formulário de nameservers está vazio e não há aviso visível de solicitação pendente, transição ou recibo. Isso não prova rejeição do envio anterior.

### Delegação e DS

- Consultas NS diretamente aos seis servidores `.br` (`a.dns.br` a `f.dns.br`) retornaram `NOERROR` e os nameservers antigos `b.sec.dns.br` e `c.sec.dns.br`.
- Consultas DS diretamente aos mesmos seis servidores retornaram tag `46835`, algoritmo `13`, digest type `2`, TTL de `3600` segundos.
- Os resolvedores recursivos `1.1.1.1` e `8.8.8.8` também retornaram os nameservers antigos.

### Validação DNSSEC e Lark

Consultas DNS-over-HTTPS ao resolvedor validador Google retornaram status DNS `0` e flag `AD=true` para MX, TXT no apex, DMARC e DKIM. Os três MX do Lark e os TXT de SPF, verificação Lark, DKIM e DMARC estão presentes. Valores de verificação e chave DKIM não foram incluídos no relatório. Consultas recursivas a `1.1.1.1` também retornaram os três MX e os quatro TXT sem `SERVFAIL`.

### Cloudflare e janela

A zona `wstecnologiaaplicada.com.br` continua no plano Free da conta `Samusilvadev`, com sete registros DNS e estado `pending` até a delegação. Não há configuração de DNSSEC Cloudflare.

O último horário observável da sessão autenticada do Registro.br é 19:52 -03:00, após o redirecionamento para login. O snapshot DNS foi às 20:37 -03:00, ainda dentro da janela documentada pelo Registro.br: publicação de nameservers após pelo menos duas horas para remoção da chave DNSSEC e transição completa que pode levar até três horas. Portanto, não considero a ausência de mudança imediata como rejeição. Monitorar até **22:52 -03:00** (três horas a partir do limite temporal observável); se permanecer inconclusivo, consultar o suporte oficial antes de qualquer nova solicitação.

```text
REQUEST_STATUS=SUBMITTED_UNCONFIRMED_WITHIN_REGISTRO_BR_WINDOW
OLD_DS=PRESENT_TAG_46835_TTL_3600_ON_ALL_SIX_PARENTS
PARENT_NAMESERVERS=OLD_B_SEC_AND_C_SEC_ON_ALL_SIX_PARENTS
CLOUDFLARE_ZONE=PENDING_FREE_7_RECORDS
LARK_DNS=PASS_MX_SPF_VERIFICATION_DKIM_DMARC
DNSSEC_VALIDATION=PASS_GOOGLE_AD_TRUE_STATUS_0
RESUBMISSION=NO
SAFE_TO_RETRY=UNKNOWN
NEXT_ACTION=MONITOR_UNTIL_22_52_THEN_OFFICIAL_SUPPORT_IF_INCONCLUSIVE
```

## V9 Recovery — investigação após a janela

Verificações realizadas em **2026-11-06**, horário de Brasília (UTC−3). O fim da janela de transição e a ausência de mudança observável não foram tratados como prova de rejeição.

### Registro.br e estado da tentativa

Às **07:21**, no painel autenticado, o domínio aparecia como publicado e utilizando os servidores DNS do Registro.br. Não havia aviso de transição, recibo ou estado pendente visível na administração do domínio. A visualização de tickets antigos não exibiu registro da tentativa. Esses sinais não confirmam se o envio anterior foi aceito ou rejeitado.

Como o estado permaneceu inconclusivo depois da janela documentada, foi enviada às **07:23:34** uma única consulta de suporte para `hostmaster@registro.br`, canal oficial indicado na [ajuda do Registro.br](https://registro.br/ajuda/gerenciamento-de-conta). A mensagem pergunta se a solicitação anterior foi recebida, está pendente, foi aceita, rejeitada/cancelada ou não consta no sistema, sem incluir credenciais ou códigos de autenticação. Nenhuma resposta havia chegado até **07:26:38**. Não houve reenvio do formulário.

### DNS, DNSSEC e Lark

Às **07:28:02**, consultas diretas a `a.dns.br` até `f.dns.br` retornaram, em todos os seis servidores, o DS `46835 / algoritmo 13 / digest type 2`, TTL de `3600` segundos, e a delegação antiga para `b.sec.dns.br` e `c.sec.dns.br`.

Na mesma rodada, `1.1.1.1` e `8.8.8.8` também retornaram os nameservers antigos e os três MX do Lark (`mx1`, `mx2` e `mx3.larksuite.com`). Às **07:28:03**, o Google DNS-over-HTTPS respondeu status `0` e `AD=true` para MX, TXT do apex, DMARC e DKIM. Os três MX e os quatro TXT esperados — SPF, verificação Lark, DKIM e DMARC — estavam presentes. Os conteúdos de verificação e da chave DKIM foram omitidos.

Também às **07:28:03**, consultas diretas a `ali.ns.cloudflare.com` e `apollo.ns.cloudflare.com` receberam resposta SOA e encontraram os mesmos três MX e quatro TXT do Lark. Isso confirma que os servidores Cloudflare respondem pela zona preparada, mas os pais .br ainda não delegam o domínio a eles.

O último estado autenticado disponível no painel Cloudflare permanece o snapshot de **2026-11-05 20:37:24**, que mostrava a zona no plano Free, `7/200` registros e estado `pending`. O painel Cloudflare não carregou nesta rodada; por isso esse estado de conta não foi renovado. A delegação pública atual ainda está nos servidores do Registro.br.

### Classificação e próximos passos

Não há evidência pública ou no painel de transição iniciada, e também não há confirmação de rejeição. A solicitação continua **desconhecida e não pode ser reenviada**. A consulta oficial enviada é a próxima fonte de confirmação; se o suporte exigir autenticação ou dados adicionais, deve-se usar o procedimento oficial indicado por ele.

```text
REQUEST_STATUS=UNKNOWN_AFTER_WINDOW_SUPPORT_QUERY_SENT_NO_REPLY_AT_07_26
OLD_DS=PRESENT_46835_ALG13_DIGEST2_TTL3600_ON_ALL_SIX_PARENTS
NEW_DS=NOT_CONFIGURED
PARENT_NAMESERVERS=OLD_B_SEC_AND_C_SEC_ON_ALL_SIX_PARENTS
CLOUDFLARE_ZONE=PENDING_LAST_DASHBOARD_OBSERVATION_2026-11-05_20_37; CURRENT_UI_NOT_REFRESHED
LARK_DNS=PASS_MX_SPF_VERIFICATION_DKIM_DMARC_ON_PUBLIC_AND_CLOUDFLARE_NS
DNSSEC_VALIDATION=PASS_GOOGLE_DOH_STATUS0_AD_TRUE; OLD_CHAIN_STILL_VALID
DELEGATION_STATUS=REQUEST_STATUS_UNKNOWN; NO_PUBLIC_TRANSITION
SAFE_TO_RETRY=NO_WITHOUT_CONFIRMED_NONRECEIPT_OR_REJECTION_AND_NEW_OWNER_AUTHORIZATION
RETRY_EXECUTED=NO
SUPPORT_QUERY=EMAIL_SENT_TO_OFFICIAL_REGISTRO_BR_AT_2026-11-06_07_23_34_BRT; NO_REPLY_BY_07_26_38
CLOUDFLARE_ACCESS=NOT_CREATED
CLOUDFLARE_TUNNEL=NOT_CREATED
PUBLIC_HOSTNAME=NOT_CREATED
HTTPS=NOT_TESTED
CHATGPT_WORK_REAL_TEST=NOT_RUN
CUSTOMER_EMAIL_SENT=NO
PRODUCTION_SERVICES_CHANGED=NO
UNRELATED_DNS_CHANGED=NO
MERGE=NO
NEXT_ACTION=AWAIT_OFFICIAL_SUPPORT_STATUS; DO_NOT_RESUBMIT
```

## V10 Final Recovery — solicitação única aceita, transição em curso

Data das observações: **2026-11-06**, horário de Brasília (UTC−3).

### Confirmação do suporte e pré-verificação

Foi lida a resposta recebida de `hostmaster@registro.br`, na thread com assunto `Re: [BR-2026110619.43] Consulta de status de solicitação DNS — wstecnologiaaplicada.com.br`, às **11:25:51**. O suporte informou que não identificou a tentativa anterior e que o encerramento da sessão provavelmente impediu seu registro; orientou autenticar novamente e refazer a solicitação pelo painel.

Antes da nova submissão, às **21:09:58**, consultas aos seis pais `.br` ainda mostravam DS `46835/13/2` (TTL `3600`) e os NS antigos. `1.1.1.1`, `8.8.8.8` e Google DoH confirmaram a delegação antiga, os três MX Lark e respostas validadas (`Status=0`, `AD=true`) para MX, TXT, DMARC e DKIM.

Na conta **Samusilvadev**, o painel Cloudflare mostrou a zona no plano Free, estado `pending` e `7/200` registros. As consultas diretas às quatro autoridades (`b.sec.dns.br`, `c.sec.dns.br`, `ali.ns.cloudflare.com`, `apollo.ns.cloudflare.com`) encontraram sete registros em cada uma: três MX, dois TXT no apex, um DMARC e um DKIM. As duas autoridades antigas coincidiram entre si, as duas Cloudflare coincidiram entre si e as listas de conteúdo corresponderam exatamente. SPF e verificação do Lark estavam presentes. Conteúdos dos TXT de verificação e DKIM não foram copiados para o relatório.

Às **21:12**, a sessão autenticada do Registro.br exibiu o domínio `wstecnologiaaplicada.com.br`, publicado e ainda sob DNS do Registro.br. O formulário continha somente `ali.ns.cloudflare.com` e `apollo.ns.cloudflare.com`; a pré-verificação passou.

### Submissão e estado DNS imediato

O botão final de confirmação foi acionado **uma única vez**, às **2026-11-06 21:13:30 -03:00**. Não foi exibido número de protocolo. O painel removeu o formulário e passou a mostrar os dois NS aprovados e o aviso de que o domínio está “em transição”, com servidores externos elegíveis à delegação em aproximadamente **1h59m45s**. Isso confirma o aceite do fluxo pelo painel, mas não a conclusão da delegação.

Consulta aos seis pais às **21:14:54** ainda retornou o DS antigo `46835/13/2`, TTL `3600`, e `b.sec.dns.br` / `c.sec.dns.br`. `1.1.1.1` e `8.8.8.8` também continuavam na delegação antiga. Google DoH manteve `Status=0`, `AD=true`, os três MX e os quatro TXT do Lark. Essa é a observação imediatamente posterior à submissão, durante a janela de transição; não indica falha nem autoriza novo envio.

### Estado e próximas validações

```text
SUPPORT_CONFIRMATION=RECEIVED_FROM_HOSTMASTER_2026-11-06_11_25_51_BRT; PREVIOUS_REQUEST_NOT_FOUND; SESSION_EXPIRY_PROBABLE
PREVIOUS_REQUEST=NOT_FOUND_BY_OFFICIAL_SUPPORT
NEW_REQUEST_AUTHORIZATION=ONE_ATTEMPT; USED_ONCE
PREFLIGHT=PASS_EXACT_7_RECORDS_ON_2_OLD_AND_2_CLOUDFLARE_AUTHORITIES; CLOUDFLARE_ACCOUNT_SAMUSILVADEV_FREE
REQUEST_SUBMISSION=SUBMITTED_ONCE; PANEL_ACKNOWLEDGED_DNS_TRANSITION
REQUEST_RECEIPT=NO_PROTOCOL_NUMBER; PANEL_SHOWED_APPROVED_NS_AND_TRANSITION_TIMER
REQUEST_SUBMISSION_TIME=2026-11-06T21:13:30-03:00
OLD_DS=PRESENT_46835_ALG13_DIGEST2_TTL3600_ON_ALL_SIX_PARENTS_AT_21_14_54
NEW_DS=NOT_CONFIGURED
PARENT_NAMESERVERS=OLD_B_SEC_AND_C_SEC_ON_ALL_SIX_PARENTS_AT_21_14_54
CLOUDFLARE_ZONE=PENDING_FREE_7_RECORDS; DIRECT_AUTHORITIES_MATCH
DELEGATION_STATUS=DELEGATION_IN_PROGRESS; PANEL_ESTIMATE_APPROX_1H59M45S
LARK_MX=PASS_3_TARGETS_AND_PRIORITIES_1_5_10
LARK_SPF=PASS
LARK_DKIM=PASS
LARK_DMARC=PASS
LARK_VERIFICATION=PASS
DNSSEC_VALIDATION=PASS_GOOGLE_DOH_STATUS0_AD_TRUE; OLD_CHAIN_STILL_VALID; OLD_DS_NOT_REMOVED
TUNNEL=NOT_CREATED
ACCESS_APPLICATION=NOT_CREATED
ACCESS_ALLOWED_EMAIL=comercial@wstecnologiaaplicada.com.br
PUBLIC_HOSTNAME=NOT_CREATED
HTTPS=NOT_TESTED
CENTRAL_COMERCIAL_HEALTH=NOT_TESTED
CHATGPT_WORK_REAL_TEST=NOT_RUN
REAL_EMAIL_SENT=NO
UNRELATED_DNS_CHANGED=NO
EXISTING_VPS_CHANGED=NO
MERGE=NO
NEXT_ACTION=READ_ONLY_RECHECK_AROUND_2026-11-06_23_13_BRT; REQUIRE_OLD_DS_ABSENT_NEW_NS_AT_ALL_SIX_PARENTS_LARK_PASS_AND_CLOUDFLARE_ACTIVE_BEFORE_NEXT_STAGE
```

O DS novo do Cloudflare não foi ativado nem publicado. Mesmo após delegação estável, sua publicação no Registro.br continua dependendo de autorização específica. Tunnel, Access, rota pública e testes da Central permanecem pendentes até a zona estar ativa.

## V11 Post Transition — delegação concluída; Access bloqueado pelo checkout Free

Observações atuais em **2026-11-07**, horário de Brasília (UTC−3), entre **09:36 e 09:41**.

### Delegação, DNSSEC e Lark

Às **09:36:12**, consultas NS diretas a `a.dns.br` até `f.dns.br` retornaram, em todos os seis servidores, `ali.ns.cloudflare.com` e `apollo.ns.cloudflare.com`. `1.1.1.1` e `8.8.8.8` também retornaram o mesmo par. O TTL observado na delegação dos pais foi **3600 segundos** e o RRset NS retornado pelo Google tinha TTL **21600 segundos**; os resolvedores consultados não mostraram mais os NS antigos.

Consultas DS com DNS-over-HTTPS do Google e Cloudflare, às **09:41**, responderam `Status=0`, sem resposta DS. A autoridade `com.br` devolveu SOA/NSEC3; não houve `SERVFAIL`. Depois de habilitar a assinatura na zona Cloudflare, o Google retornou NS e MX com RRSIG, `AD=false`, comportamento esperado enquanto o DS novo não estiver publicado no pai. Portanto, não há falha de DNSSEC, mas a cadeia ainda não é validada como segura até a publicação autorizada do DS.

Na conta **Samusilvadev**, o painel mostrou a zona ativa, plano Free, `DNS Setup: Full`, os nameservers aprovados e `7/200` registros. As duas autoridades Cloudflare e os resolvedores públicos responderam com o inventário Lark:

- MX: `mx1.larksuite.com` prioridade 1; `mx2.larksuite.com` prioridade 5; `mx3.larksuite.com` prioridade 10.
- SPF: presente; verificação Lark: presente; DKIM `lark2610221127._domainkey`: presente; DMARC: `v=DMARC1; p=none;`.
- Os valores integrais do TXT de verificação e da chave DKIM não foram copiados para o relatório. Nenhum dos sete registros foi alterado.

O painel Cloudflare avisou que não há A/AAAA/CNAME para o apex nem para `www`. Consultas autoritativas atuais confirmaram NODATA para A/AAAA no apex e NXDOMAIN para `www`. Nenhum destino web foi fornecido; não foi inventado nem alterado registro de site. A disponibilidade do site nesses nomes não foi comprovada nesta rodada.

DNSSEC foi habilitado no Cloudflare apenas para preparar a assinatura. A interface mostra estado **pending**, aguardando DS no Registro.br. DS preparado: **2371 13 2 9988E1950F146843EF3F982F6FA19EF0DA3F597903EF7E23BA36DF09603F4648**. O DS não foi publicado no Registro.br.

### Central Comercial e bloqueio de Access

O hostname `central-comercial.wstecnologiaaplicada.com.br` continua sem registro DNS; consultas às duas autoridades Cloudflare retornaram inexistência, sem conflito. Cloudflare Access ainda não tem aplicação configurada e o onboarding Zero Trust não foi concluído.

O login `cloudflared` foi autorizado exclusivamente para a zona aprovada; o certificado de origem ficou no perfil Windows, com ACL para o usuário, Administradores locais e SYSTEM. `cloudflared tunnel list` confirmou **nenhum Tunnel existente**. Não foi criado Tunnel nem rota DNS, respeitando a ordem de proteger Access primeiro.

O painel ofereceu Zero Trust Free a **US$ 0/mês** para até 50 usuários, mas apresentou uma caixa separada que autoriza cobranças mensais por uso acima da cota. O proprietário autorizou aceitar os Termos e ativar Free sem overage. Mesmo com o aceite dos Termos marcado e a autorização de overage desmarcada, o checkout recusou a ativação com “You need to agree to the terms above to continue.” O checkout foi fechado; a tela voltou a “Welcome to Cloudflare Zero Trust”. Nenhuma autorização de cobrança foi dada e o plano não foi ativado.

No ambiente privado `%LOCALAPPDATA%\CentralComercial\central-comercial.env`, `CENTRAL_PUBLIC_ORIGIN` foi atualizado para `https://central-comercial.wstecnologiaaplicada.com.br`; hash de senha, segredo de sessão e credenciais Lark permaneceram idênticos, e a ACL do arquivo não mudou. A suíte local executou **22 testes, todos aprovados**, incluindo login/logout, cookies seguros, CSRF, Host/Origin, PDF e prévia; não houve envio SMTP real. O health check local respondeu `200 ok` com Host aprovado e `400` com Host incompatível. O runtime foi encerrado após a verificação; enquanto esteve ativo, escutou somente em `127.0.0.1`. HTTPS público, sessão autenticada em produção e ChatGPT Work não foram testados, pois Access e Tunnel permanecem bloqueados.

```text
OBSERVATION_TIME=2026-11-07 09:36–09:41 -03
OLD_DS=ABSENT_IN_GOOGLE_AND_CLOUDFLARE_DOH; NO_PARENT_DS_ANSWER
PARENT_NS=ALI_AND_APOLLO_ON_ALL_SIX_BR_AUTHORITIES
CLOUDFLARE_ZONE=ACTIVE_FREE; 7_RECORDS
DNSSEC_VALIDATION=NO_SERVFAIL; CHILD_SIGNED; AD_FALSE_PENDING_PARENT_DS
LARK_DNS=PASS; ALL_SEVEN_PRESENT; NO_RECORDS_CHANGED
NEW_DS=2371 13 2 9988E1950F146843EF3F982F6FA19EF0DA3F597903EF7E23BA36DF09603F4648
NEW_DS_PUBLISHED=NO
ACCESS=NOT_CONFIGURED; ZERO_TRUST_FREE_CHECKOUT_VALIDATION_BLOCKED
TUNNEL=NONE_EXISTING; NOT_CREATED_BEFORE_ACCESS
HOSTNAME_DNS=ABSENT; NO_CONFLICT
CENTRAL_ORIGIN=HTTPS_CONFIGURED_IN_PRIVATE_ENV; SECRETS_AND_ACL_PRESERVED
LOCAL_TESTS=22_PASS; HEALTHZ_PASS_WITH_APPROVED_HOST
HTTPS=NOT_TESTED; PANEL_AUTH=UNIT_TESTS_PASS_LIVE_NOT_TESTED
CHATGPT_WORK=NOT_TESTED
RESUBMISSION=NO
REAL_EMAIL_SENT=NO
MERGE=NO
NEXT_ACTION=REQUEST_CLOUDFLARE_RESOLUTION_FOR_FREE_ACTIVATION_WITHOUT_OVERAGE; THEN_CONFIGURE_ACCESS_BEFORE_TUNNEL_OR_DNS
RESULT=PARTIAL
```


## V12 Zero Trust Free — onboarding bloqueado; nenhuma cobrança autorizada

Observações em **2026-11-07, 13:08–13:16 UTC (10:08–10:16 BRT)**.

### Conta e checkout

- O dashboard autenticado exibiu a conta escolhida **Samusilvadev**. A página Zero Trust mostrou “Welcome to Cloudflare Zero Trust” e “Get started”; não há organização Zero Trust criada.
- O caminho oficial “Get started” abriu a seleção de planos. O cartão Zero Trust Free indicou **US$ 0 por assento/mês** e limite de 50 usuários. Ao selecionar Free, o dashboard navegou para /zero-trust/checkout/free, mas a página ficou branca, sem campos de pagamento, termos, opção de overage ou botão de envio visíveis. Não houve novo envio.
- No checkout observado em V11, marcar os Termos e deixar a autorização de overage desmarcada resultou em **“You need to agree to the terms above to continue.”** O plano não foi ativado. Neste V12 nenhum termo foi aceito novamente, nenhum dado de pagamento foi digitado, overage segue não autorizado e nenhuma assinatura paga foi criada.
- A [documentação atual do Cloudflare](https://developers.cloudflare.com/learning-paths/cybersafe/account-creation/create-zero-trust-org/) diz que criar uma organização Zero Trust requer selecionar o plano e informar payment details; também diz que o plano Free não gera cobrança. O método de pagamento existente visto em V11 não foi alterado; a página em branco não permite determinar se ele atende ao requisito ou se há falha de validação. A documentação aponta para o mesmo onboarding do dashboard e não apresenta caminho alternativo oficial de ativação Free.
- A [página de status](https://www.cloudflarestatus.com/services) consultada mostrava Zero Trust e Zero Trust Dashboard operacionais; a busca oficial pela mensagem exata não encontrou um aviso de incidente. Isso não descarta problema específico da conta ou da interface.
- Os [canais oficiais de suporte](https://developers.cloudflare.com/support/contacting-cloudflare-support/) informam que contas Free podem abrir casos para billing, account e registrar issues e recomendam Cloudflare Community para troubleshooting. Nenhum ticket, post ou mensagem foi enviado; o relato técnico está preparado para envio pelo proprietário, sem segredos ou dados de cartão.

### DNS e DNSSEC — nova observação

Às **13:12:49 UTC**, 1.1.1.1 respondeu com ali.ns.cloudflare.com e apollo.ns.cloudflare.com (TTL observado **86400 s**). As autoridades Cloudflare responderam aos registros Lark; 1.1.1.1 e 8.8.8.8 resolveram os três MX. Não foi observado SERVFAIL.

Às **13:15:55 UTC**, Google DNS-over-HTTPS retornou consulta DS com Status=0, zero respostas e seis registros de autoridade; AD=false. A zona serviu duas DNSKEYs. O DS SHA-256 recalculado da DNSKEY atual corresponde ao DS preparado:

**2371 13 2 9988E1950F146843EF3F982F6FA19EF0DA3F597903EF7E23BA36DF09603F4648**

O pai ainda não publica DS. Assim, os registros assinados do filho não formam uma cadeia validada por DNSSEC nesta observação (AD=false); não se declara DNSSEC plenamente validado. O novo DS não foi publicado.

Os sete registros Lark permanecem presentes: MX de prioridades 1/5/10; dois TXT no apex (SPF e outro TXT de verificação já identificado como Lark), um DKIM e um DMARC. O valor de verificação e a chave DKIM foram omitidos. Nenhum registro DNS foi alterado. Consultas atuais também não encontraram A/AAAA/CNAME para central-comercial.wstecnologiaaplicada.com.br.

### Estado de implantação e CI

Zero Trust ainda não está provisionado; Access não existe. Nenhum Tunnel foi criado, nenhuma rota DNS do hostname foi criada e HTTPS público não foi testado. Login da Central, PDF, prévia, cookies, CSRF, Origin/Host, logout e ChatGPT Work continuam sem teste público. Nenhum e-mail real foi enviado; nenhum outro serviço foi modificado; nenhum merge foi executado.

Na revisão do HEAD 6659a3d9ba6774e3eaaa4c730bbbde3f6462ada2, os dois checks unit-tests concluíram com sucesso. Anotações foram somente avisos de depreciação do Node.js 20 nos actions e da futura migração de ubuntu-latest; sem falhas de teste. Os 22 testes locais descritos em V11 passaram; V12 não alterou código de aplicação.

### Estado resumido

CAMPAIGN=TEC_COMERCIAL_ZERO_TRUST_V12_RECOVERY
OBSERVATION_TIME=2026-11-07T13:08–13:16Z
CLOUDFLARE_ACCOUNT=Samusilvadev
ZERO_TRUST_ORGANIZATION=NOT_CREATED
FREE_PLAN=NOT_ACTIVATED; FREE_CARD_DISPLAYED_USD_0; 50_SEATS
CHECKOUT_ERROR=V11_GENERIC_TERMS_VALIDATION; V12_FREE_CHECKOUT_BLANK
CHECKOUT_ROOT_CAUSE=UNRESOLVED; PAYMENT_DETAILS_REQUIRED_BY_OFFICIAL_DOCS; NO_BYPASS
PAYMENT_METHOD_REQUIRED=PAYMENT_DETAILS_REQUIRED_FOR_ONBOARDING; EXISTING_METHOD_SHOWN_V11; CURRENT_BLANK_PAGE_PREVENTS_CONFIRMING_SUFFICIENCY
OVERAGE_AUTHORIZED=NO
PAID_SUBSCRIPTION_CREATED=NO
ACCESS_APPLICATION=NOT_CREATED
ACCESS_ALLOWED_EMAIL=NOT_CONFIGURED
TUNNEL=NOT_CREATED
HOSTNAME_DNS=NO_A_AAAA_CNAME
HTTPS=NOT_TESTED
PANEL_LOGIN=NOT_TESTED_PUBLICLY
PDF_PREVIEW=NOT_TESTED_PUBLICLY
CHATGPT_WORK_REAL_TEST=NOT_RUN
PARENT_NS=ALI_AND_APOLLO_VIA_1.1.1.1_TTL_86400
PARENT_DS=NO_DS_ANSWER_STATUS0; AD_FALSE
DNSSEC_VALIDATION=INCOMPLETE_PARENT_DS_ABSENT; CURRENT_DNSKEY_MATCHES_PREPARED_DS; NO_SERVFAIL
LARK_DNS=PASS_3_MX_4_TXT; NO_CHANGES
REAL_EMAIL_SENT=NO
OTHER_SERVICES_CHANGED=NO
MERGE=NO
PR_HEAD_BEFORE_REPORT_UPDATE=6659a3d9ba6774e3eaaa4c730bbbde3f6462ada2
CI_AT_THAT_HEAD=2_UNIT_TEST_CHECKS_SUCCESS; WARNINGS_ONLY
SUPPORT_CONTACT=NOT_SENT; OFFICIAL_FREE_CHANNELS_REVIEWED; DRAFT_PREPARED
FINAL_RESULT=PARTIAL
NEXT_ACTION=OWNER_TO_ASK_CLOUDFLARE_ACCOUNT_SUPPORT_OR_COMMUNITY_HOW_TO_COMPLETE_FREE_ONBOARDING_WITHOUT_OVERAGE; STOP_IF_NEW_PAYMENT_DETAILS_OR_OVERAGE_AUTHORIZATION_REQUIRED
