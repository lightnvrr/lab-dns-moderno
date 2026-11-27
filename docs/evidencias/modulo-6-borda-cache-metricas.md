# Issue #4: Borda — cache, encaminhamento e métricas

Data: 26/11/2026.
Ambiente: Windows 11, PowerShell no VS Code, Docker Desktop com WSL 2.

## 1. Análise do `borda/Corefile`

O arquivo `borda/Corefile` configura o CoreDNS responsável por receber as consultas DNS dos clientes.

O bloco `(resolver)` reúne as configurações compartilhadas pelos três protocolos:

- `log`: registra as consultas recebidas.
- `errors`: registra erros durante o processamento.
- `hosts`: aplica a lista de bloqueio definida em `bloqueio.hosts`.
- `ttl 10`: define o TTL das entradas do arquivo de bloqueio.
- `reload 2s`: verifica alterações na lista de bloqueio a cada 2 segundos.
- `fallthrough`: permite que consultas não encontradas na lista continuem para os próximos plugins.
- `cache 300`: habilita o cache DNS com duração máxima de 300 segundos.
- `forward . 172.20.0.20`: encaminha as consultas ao Unbound.
- `prometheus 0.0.0.0:9153`: disponibiliza as métricas do CoreDNS na porta 9153.

Os blocos seguintes reutilizam essas configurações por meio de `import resolver`:

- `.:53`: atende consultas DNS convencionais.
- `tls://.:853`: atende consultas DNS over TLS.
- `https://.:443`: atende consultas DNS over HTTPS.

O bloco `use-application-dns.net` responde com NXDOMAIN para evitar que o Firefox habilite automaticamente seu DoH.

Os três blocos `geo.internal` implementam o GeoDNS: clientes da região A recebem `10.1.0.10`, clientes da região B recebem `10.2.0.10` e os demais recebem `10.0.0.10`.

**Observação:** o Corefile foi analisado sem alterações, preservando a configuração original do projeto.

## 2. Demonstração do cache DNS

Comando executado:

```powershell
docker compose exec cliente-a bash -c "dig @172.21.0.53 ufal.br +noall +answer; sleep 5; dig @172.21.0.53 ufal.br +noall +answer"
```

Resultado:

```text
ufal.br. 300 IN A 200.17.112.70
ufal.br. 295 IN A 200.17.112.70
```

O TTL diminuiu de 300 para 295 segundos após cinco segundos. Isso demonstra que a segunda consulta utilizou a resposta armazenada no cache DNS.

## 3. Verificação das métricas do CoreDNS

Foi acessado o endpoint:

`http://localhost:9153/metrics`

Também foi executado:

```powershell
curl.exe -i http://localhost:9153/metrics
```

Resultado observado:

```text
HTTP/1.1 200 OK
Content-Type: text/plain; version=0.0.4
```

Entre as métricas encontradas:

```text
coredns_cache_entries{server="dns://:53",type="success",view=""} 1
coredns_cache_hits_total{server="dns://:53",view=""} 1
coredns_cache_misses_total{server="dns://:53",view=""} 1
coredns_cache_requests_total{server="dns://:53",view=""} 2
coredns_dns_requests_total{family="1",proto="udp",server="dns://:53",type="A",view="",zone="."} 2
```

A resposta HTTP 200 confirma que o endpoint de métricas está funcionando. As métricas também mostram duas consultas DNS, um acerto e uma falta no cache.

## 4. Como explicar no vídeo

O CoreDNS funciona como a borda do laboratório, recebendo consultas DNS convencionais, DoT e DoH. As consultas são encaminhadas ao Unbound quando necessário, enquanto o cache evita repetir consultas já respondidas. A demonstração mostrou o TTL diminuindo de 300 para 295 segundos, indicando o uso do cache. Por fim, o Prometheus disponibiliza métricas na porta 9153, permitindo acompanhar as consultas e o funcionamento do cache.
