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

```text
PRE_SUBMIT_INVENTORY=PASS_EXACT_7
PRE_SUBMIT_CLOUDFLARE_NS_AUTHORITY=PASS_BOTH
REGISTRO_BR_REQUEST=SUBMIT_ATTEMPTED_UNCONFIRMED
REGISTRO_BR_SESSION=RELOGIN_REQUIRED
OLD_DS=STILL_PUBLISHED_TTL_3600
PUBLIC_NS=STILL_REGISTRO_BR_AT_LAST_CHECK
LARK_MX=RESOLVING_AT_LAST_CHECK
RESUBMISSION=NO
DNSSEC_CLOUDFLARE=NOT_CONFIGURED
TUNNEL_ACCESS=NOT_CREATED
PRODUCTION_CHANGED=NO_CONFIRMED_CHANGE
```
