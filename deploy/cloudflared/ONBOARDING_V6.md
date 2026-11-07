# Cloudflare zone onboarding — V6

Data da verificação: 2026-11-05

## Estado confirmado

| Item | Estado |
| --- | --- |
| Conta | Conta Cloudflare escolhida pelo proprietário: Samusilvadev |
| Zona | `wstecnologiaaplicada.com.br`, criada no plano Free |
| Ativação | Pendente; o painel aguarda alteração de nameservers |
| Nameservers atribuídos | `ali.ns.cloudflare.com`, `apollo.ns.cloudflare.com` |
| Nameservers atuais | `b.sec.dns.br`, `c.sec.dns.br` |
| Mudança no Registro.br | Não executada |
| Alteração em produção | Não executada |
| Email Routing / Workers / VPS / aplicações | Não alterados |
| Bot Preference Sync | Desativado na configuração inicial da zona |

O painel Cloudflare exibiu “Update your nameservers to activate Cloudflare”. A zona ainda não é autoritativa e os nameservers no Registro.br permanecem os atuais.

## Inventário DNS verificado no Registro.br e comparado com Cloudflare

O modo avançado da zona DNS no Registro.br apresentou sete registros. A transferência AXFR pública foi recusada, mas a tabela autenticada do Registro.br forneceu o inventário completo. O Cloudflare importou seis registros inicialmente; o DKIM ausente foi adicionado à zona pendente a partir da fonte autenticada. Os sete registros Cloudflare estão DNS-only.

| Tipo | Nome | Valor | Estado |
| --- | --- | --- | --- |
| MX | `@` | `mx1.larksuite.com`, prioridade 1 | Preservado |
| MX | `@` | `mx2.larksuite.com`, prioridade 5 | Preservado |
| MX | `@` | `mx3.larksuite.com`, prioridade 10 | Preservado |
| TXT | `@` | `v=spf1 +include:spf.onlarksuite.com -all` | Preservado |
| TXT | `_dmarc` | `v=DMARC1; p=none;` | Preservado |
| TXT | `@` | Verificação do Lark presente | Preservado; conteúdo omitido deste relatório |
| TXT | `lark2610221127._domainkey` | DKIM do Lark; chave pública conferida sem reproduzi-la aqui | Adicionado e validado como equivalente ao registro do Registro.br |

Não há registros A, AAAA ou CNAME no apex nem em `www` na tabela do Registro.br ou na zona Cloudflare. O destino de hospedagem do site não está definido por esses registros; nenhum destino foi inventado. A tabela autenticada do Registro.br não apresenta outros registros DNS.

**Inventário DNS = PASS.** A comparação foi feita linha por linha entre a tabela avançada do Registro.br e a zona Cloudflare recarregada. A zona Cloudflare passou a exibir sete registros, incluindo o DKIM do Lark. Nenhum registro de site foi criado sem destino confirmado.

## DNSSEC atual

DNSSEC está ativo no DNS atual. Os servidores `.br` retornam o DS abaixo, e o DNS atual retorna DNSKEY/RRSIG; consultas DNS públicas não falharam na validação:

```text
DS: 46835 13 2 3b9db6853fbb66883fea5b0280bf64e493647f5e318c01648bf10547a43c3cf2
DNSKEY flags: 257; algorithm: 13
```

Antes de mudar nameservers, remover o DS atual no Registro.br e confirmar que não resta DS publicado. Não publicar esse DS antigo para a nova zona Cloudflare.

Referências Cloudflare: [setup completo](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/), [troubleshooting do setup completo](https://developers.cloudflare.com/dns/zone-setups/full-setup/troubleshooting/), [DNSSEC](https://developers.cloudflare.com/dns/dnssec/) e [status da zona](https://developers.cloudflare.com/dns/zone-setups/reference/domain-status/).

## Plano seguro de migração

### Antes de qualquer mudança de delegação

1. O inventário foi lido na tabela avançada autenticada do Registro.br e tem sete registros; não havia A, AAAA, CNAME, SRV, CAA, TLSA ou registros adicionais nessa tabela.
2. Os sete registros foram comparados com Cloudflare; o único ausente era o TXT DKIM, já adicionado. MX, SPF, DKIM, DMARC e verificação Lark permanecem DNS-only.
3. Confirmar os destinos do site e dos outros serviços com o proprietário ou provedor antes de criar registros de site: o apex e `www` não possuem A/AAAA/CNAME no DNS atual.
4. Confirmar que a aplicação Cloudflare Access do hostname comercial foi configurada com Allow exclusivo ao email aprovado antes de criar qualquer DNS público para o Tunnel, conforme `ACTIVATION_V5.md`.
5. Obter autorização específica para trocar nameservers. Ela ainda não foi dada nesta etapa.

### Delegação

1. No Registro.br, desativar DNSSEC/remover o DS atual antes da troca de nameservers; confirmar a remoção por consultas aos servidores `.br` e validadores públicos.
2. Somente após autorização específica, substituir no Registro.br `b.sec.dns.br` e `c.sec.dns.br` por `ali.ns.cloudflare.com` e `apollo.ns.cloudflare.com`.
3. Acompanhar propagação e validar que as respostas autoritativas Cloudflare contêm o inventário reconciliado, sem perda de email, site ou outros serviços.
4. Depois de a zona estar ativa e estável, habilitar DNSSEC no Cloudflare e cadastrar no Registro.br somente o novo DS emitido pelo Cloudflare. Validar novamente por resolvers DNSSEC.

## Rollback

1. Se houver falha após a delegação e DNSSEC Cloudflare estiver habilitado, remover primeiro o DS Cloudflare no Registro.br e confirmar que não é mais publicado.
2. Restaurar `b.sec.dns.br` e `c.sec.dns.br`; não alterar os registros do provedor DNS antigo.
3. Confirmar propagação e validar o site, email e serviços no DNS antigo.
4. Restaurar o DS antigo acima apenas depois que os nameservers e DNSKEY antigos estiverem novamente servindo e o digest tiver sido revalidado. Não restaurar o DS antigo enquanto a delegação aponta ao Cloudflare.

## Resultado desta preparação

```text
CLOUDFLARE_ZONE=CREATED_PENDING_DELEGATION
DNS_INVENTORY=PASS
LARK_RECORDS=PRESERVED
DNSSEC=VERIFIED_CURRENT_DS_PUBLISHED
NAMESERVER_CHANGE=NOT_EXECUTED
PRODUCTION_CHANGED=NO
```
