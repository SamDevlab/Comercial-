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
