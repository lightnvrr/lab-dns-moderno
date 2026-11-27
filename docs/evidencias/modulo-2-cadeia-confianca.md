# Issue #3: Módulo 2, resolvedor validador e cadeia de confiança

Máquina: Windows 11 Home, PowerShell, Docker Desktop 29.9.3.
Data: 27/11/2026 (horário dos contêineres em UTC).

Antes de começar, o computador tinha sido reiniciado e o Docker Desktop não abre sozinho.
Depois de abrir o Docker Desktop, bastou subir os contêineres de novo. O `preparar.sh` não foi
rodado outra vez, porque as chaves e o `lab.ds` continuam no disco:

```powershell
docker compose up -d
docker compose ps
```

```
SERVICE        STATE     STATUS
autoritativo   running   Up 9 seconds
borda          running   Up 8 seconds
cliente-a      running   Up 9 seconds
cliente-b      running   Up 9 seconds
resolvedor     running   Up 9 seconds
```

## Como a cadeia de confiança funciona (para ler antes das saídas)

Cada zona assina os próprios registros com a sua chave (DNSKEY). Mas como o resolvedor sabe
que a DNSKEY é verdadeira? Porque a **zona pai** publica um **DS**, que é um resumo (hash) da
chave da filha, e esse DS é assinado pela chave do pai. Subindo de pai em pai, chega-se à
**raiz**, que não tem pai. A chave da raiz então precisa vir **instalada** no resolvedor: é
a **âncora de confiança**.

```
âncora (root.key: KSK 38696)
  └─ assina a DNSKEY da raiz  ──► DS de .br
        └─ DNSKEY de .br      ──► DS de registro.br
              └─ DNSKEY de registro.br ──► assina o registro A de registro.br
```

A zona `lab.internal` não existe na internet e não tem pai que publique o DS dela. Por isso
o DS vai direto para o resolvedor, no arquivo `lab.ds`, que faz o papel da âncora.

## 1. O DS em `resolvedor/lab.ds` e o papel dele

```powershell
Get-Content resolvedor/lab.ds
```

```
lab.internal. IN DS 50164 13 2 9F06239062AA746FF2C9F3CE41951014D3676E082685FD2CF0BE0D11356B2FBA
```

Lendo o registro: `50164` é a tag (o "apelido") da chave que ele representa, `13` é o
algoritmo (ECDSA P-256 com SHA-256), `2` é o tipo de resumo (SHA-256) e o resto é o resumo
da chave. O DS **não é a chave**: é uma impressão digital dela, e por isso pode ser público.

O Unbound carrega esse arquivo como âncora:

```powershell
Select-String -Path resolvedor/unbound.conf -Pattern "anchor"
```

```
resolvedor\unbound.conf:12:    auto-trust-anchor-file: "/var/lib/unbound/root.key"   # raiz da internet (KSK-2024)
resolvedor\unbound.conf:13:    trust-anchor-file: "/etc/unbound/lab/lab.ds"          # zona do laboratório (gerada na assinatura)
```

Agora as chaves que o autoritativo publica de verdade:

```powershell
docker compose exec -T cliente-a dig "@172.21.0.53" lab.internal DNSKEY +multi +noall +comments +answer
```

```
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 20679
;; flags: qr rd ra ad; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1232
; COOKIE: c847a8313abb8040 (echoed)
;; ANSWER SECTION:
lab.internal.		292 IN DNSKEY 257 3 13 (
				xxnP6iurUy4llcUWaD6a7ZMiKHQomTa0kNC3KeycaD6D
				xL+NcCXM6du8EJCLu4w4WpIssbYbHKgGacXSHLw81Q==
				) ; KSK; alg = ECDSAP256SHA256 ; key id = 50164
lab.internal.		292 IN DNSKEY 256 3 13 (
				16uOyKhgoxGPV8K1E5j+Aplgs5+B6MBShI5ydBnVdq/T
				0u8boDJT87C3OSmwe6+dwLHOgnL3Ub/8FHyVUMQpjQ==
				) ; ZSK; alg = ECDSAP256SHA256 ; key id = 30805
```

A zona tem duas chaves: a **KSK** (flag `257`, tag 50164), que só assina o conjunto de chaves,
e a **ZSK** (flag `256`, tag 30805), que assina os registros comuns, como o `www` e o `banco`
da issue #2. O DS aponta para a KSK (50164), e a resposta veio com `ad`.

Por fim, a prova de que o DS é o resumo dessa KSK. Calculei o DS a partir da chave servida
pelo autoritativo e comparei com o arquivo:

```powershell
docker compose exec -T cliente-a bash -c "dig @172.21.0.53 lab.internal DNSKEY +noall +answer | dnssec-dsfromkey -2 -f - lab.internal"
```

```
lab.internal. IN DS 50164 13 2 9F06239062AA746FF2C9F3CE41951014D3676E082685FD2CF0BE0D11356B2FBA
```

É idêntico ao `lab.ds`. A conta da validação é esta: o resolvedor recebe a DNSKEY, calcula
o resumo e compara com a âncora. Se bater, ele confia na KSK. A KSK garante a ZSK, e a ZSK
garante os registros. Se alguém trocasse a chave da zona, o resumo mudaria e nada mais validaria.

## 2. A KSK-2024 (38696) no `root.key`

O arquivo do repositório, que o `Dockerfile` copia para dentro da imagem:

```powershell
Get-Content resolvedor/root.key
```

```
. IN DNSKEY 257 3 8 AwEAAaz/tAm8yTn4Mfeh5eyI96WSVexTBAvkMgJzkKTOiW1vkIbzxeF3+/4RgWOq7HrxRixHlFlExOLAJr5emLvN7SWXgnLh4+B5xQlNVz8Og8kvArMtNROxVQuCaSnIDdD5LKyWbRd2n9WGe2R8PzgCmr3EgVLrjyBxWezF0jLHwVN8efS3rCj/EWgvIWgb9tarpVUDK/b58Da+sqqls3eNbuv7pr+eoZG+SrDK6nWeL3c6H5Apxz7LjVc1uTIdsIXxuOLYA4/ilBmSVIzuDWfdRUfhHdY6+cn8HFRm+2hM8AnXGXws9555KrUB5qihylGa8subX2Nn6UwNR1AkUTV74bU= ; keytag 20326
. IN DNSKEY 257 3 8 AwEAAa96jeuknZlaeSrvyAJj6ZHv28hhOKkx3rLGXVaC6rXTsDc449/cidltpkyGwCJNnOAlFNKF2jBosZBU5eeHspaQWOmOElZsjICMQMC3aeHbGiShvZsx4wMYSjH8e7Vrhbu6irwCzVBApESjbUdpWWmEnhathWu1jo+siFUiRAAxm9qyJNg/wOZqqzL/dL/q8PkcRU5oUKEpUge71M3ej2/7CPqpdVwuMoTvoB+ZOT4YeGyxMvHmbrxlFzGOHOijtzN+u1TQNatX2XBuzZNQ1K+s2CXkPIZo7s6JgZyvaBevYtxPvYLw4z9mR7K2vaF18UYH9Z9GNUUeayffKC73PYc= ; keytag 38696
```

A versão que o Unbound mantém dentro do contêiner:

```powershell
docker compose exec -T resolvedor cat /var/lib/unbound/root.key
```

```
; autotrust trust anchor file
;;id: . 1
;;last_queried: 1795740190 ;;Fri Nov 27 00:43:10 2026
;;last_success: 1795740190 ;;Fri Nov 27 00:43:10 2026
;;next_probe_time: 1795781362 ;;Fri Nov 27 12:09:22 2026
;;query_failed: 0
;;query_interval: 43200
;;retry_time: 8640
.	3600	IN	DNSKEY	257 3 8 AwEAAa96jeuknZlaeSrvyAJj6ZHv28hhOKkx3rLGXVaC6rXTsDc449/cidltpkyGwCJNnOAlFNKF2jBosZBU5eeHspaQWOmOElZsjICMQMC3aeHbGiShvZsx4wMYSjH8e7Vrhbu6irwCzVBApESjbUdpWWmEnhathWu1jo+siFUiRAAxm9qyJNg/wOZqqzL/dL/q8PkcRU5oUKEpUge71M3ej2/7CPqpdVwuMoTvoB+ZOT4YeGyxMvHmbrxlFzGOHOijtzN+u1TQNatX2XBuzZNQ1K+s2CXkPIZo7s6JgZyvaBevYtxPvYLw4z9mR7K2vaF18UYH9Z9GNUUeayffKC73PYc= ;{id = 38696 (ksk), size = 2048b} ;;state=2 [  VALID  ] ;;count=0 ;;lastchange=1795740190 ;;Fri Nov 27 00:43:10 2026
.	3600	IN	DNSKEY	257 3 8 AwEAAaz/tAm8yTn4Mfeh5eyI96WSVexTBAvkMgJzkKTOiW1vkIbzxeF3+/4RgWOq7HrxRixHlFlExOLAJr5emLvN7SWXgnLh4+B5xQlNVz8Og8kvArMtNROxVQuCaSnIDdD5LKyWbRd2n9WGe2R8PzgCmr3EgVLrjyBxWezF0jLHwVN8efS3rCj/EWgvIWgb9tarpVUDK/b58Da+sqqls3eNbuv7pr+eoZG+SrDK6nWeL3c6H5Apxz7LjVc1uTIdsIXxuOLYA4/ilBmSVIzuDWfdRUfhHdY6+cn8HFRm+2hM8AnXGXws9555KrUB5qihylGa8subX2Nn6UwNR1AkUTV74bU= ;{id = 20326 (ksk), size = 2048b} ;;state=2 [  VALID  ] ;;count=0 ;;lastchange=1795740190 ;;Fri Nov 27 00:43:10 2026
```

O arquivo tem as duas KSKs da raiz: a **20326 (KSK-2017)** e a **38696 (KSK-2024)**, as duas
com algoritmo `8` (RSA/SHA-256) e 2048 bits. A KSK-2024 é a chave nova da raiz da internet,
criada para substituir a de 2017. Na versão do contêiner, o Unbound marca as duas como
`VALID`: o `auto-trust-anchor-file` faz ele conferir a raiz periodicamente (`query_interval`
de 43200 s, 12 horas) e atualizar a âncora sozinho quando a raiz troca de chave (RFC 5011).

E o que a raiz real publica hoje, consultada pelo laboratório:

```powershell
docker compose exec -T cliente-a dig "@172.21.0.53" . DNSKEY +multi +noall +comments +answer | Select-String -Pattern "flags|status|key id|DNSKEY 257|DNSKEY 256"
```

(Saída filtrada pelo `Select-String`, que esconde as linhas com os bytes das chaves.)

```
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 27268
;; flags: qr rd ra ad; QUERY: 1, ANSWER: 3, AUTHORITY: 0, ADDITIONAL: 1
; EDNS: version: 0, flags:; udp: 1232
.			300 IN DNSKEY 257 3 8 (
				) ; KSK; alg = RSASHA256 ; key id = 20326
.			300 IN DNSKEY 257 3 8 (
				) ; KSK; alg = RSASHA256 ; key id = 38696
.			300 IN DNSKEY 256 3 8 (
				) ; ZSK; alg = RSASHA256 ; key id = 8763
```

A raiz publica as mesmas duas KSKs que estão na âncora (20326 e 38696) e uma ZSK (8763), e a
resposta tem `ad`. Ou seja, a âncora instalada no resolvedor bate com a chave que a raiz usa.

## 3. `delv @172.21.0.53 registro.br +vtrace` com `fully validated`

```powershell
docker compose exec -T cliente-a delv "@172.21.0.53" registro.br +vtrace
```

```
;; fetch: registro.br/A
;; validating registro.br/A: starting
;; validating registro.br/A: attempting positive response validation
;; fetch: registro.br/DNSKEY
;; validating registro.br/DNSKEY: starting
;; validating registro.br/DNSKEY: attempting positive response validation
;; fetch: registro.br/DS
;; validating registro.br/DS: starting
;; validating registro.br/DS: attempting positive response validation
;; fetch: br/DNSKEY
;; validating br/DNSKEY: starting
;; validating br/DNSKEY: attempting positive response validation
;; fetch: br/DS
;; validating br/DS: starting
;; validating br/DS: attempting positive response validation
;; fetch: ./DNSKEY
;; validating ./DNSKEY: starting
;; validating ./DNSKEY: attempting positive response validation
;; validating ./DNSKEY: no RRSIG matching DS key
;; validating ./DNSKEY: verify rdataset (keyid=38696): success
;; validating ./DNSKEY: marking as secure (DS)
;; validating br/DS: in fetch_callback_dnskey
;; validating br/DS: keyset with trust secure
;; validating br/DS: resuming validate
;; validating br/DS: verify rdataset (keyid=8763): success
;; validating br/DS: marking as secure, noqname proof not needed
;; validating br/DNSKEY: in fetch_callback_ds
;; validating br/DNSKEY: dsset with trust secure
;; validating br/DNSKEY: verify rdataset (keyid=38298): success
;; validating br/DNSKEY: marking as secure (DS)
;; validating registro.br/DS: in fetch_callback_dnskey
;; validating registro.br/DS: keyset with trust secure
;; validating registro.br/DS: resuming validate
;; validating registro.br/DS: verify rdataset (keyid=32480): success
;; validating registro.br/DS: marking as secure, noqname proof not needed
;; validating registro.br/DNSKEY: in fetch_callback_ds
;; validating registro.br/DNSKEY: dsset with trust secure
;; validating registro.br/DNSKEY: verify rdataset (keyid=59973): success
;; validating registro.br/DNSKEY: marking as secure (DS)
;; validating registro.br/A: in fetch_callback_dnskey
;; validating registro.br/A: keyset with trust secure
;; validating registro.br/A: resuming validate
;; validating registro.br/A: verify rdataset (keyid=59973): success
;; validating registro.br/A: marking as secure, noqname proof not needed
; fully validated
registro.br.		300	IN	A	200.160.2.3
registro.br.		300	IN	RRSIG	A 13 2 172800 20261228084215 20261019080106 59973 registro.br. rfTYPHHhYfuOe/+KzYBG7Ssz+l1msS5+DJFouNiDMbSjTeI7ltmI7/lD wvFHphwsWNeqKlraLiB2vmCREftcdA==
```

O `delv` refaz a validação por conta própria, com a âncora da raiz embutida nele, e o `+vtrace`
mostra cada passo. Primeiro ele **desce** buscando o que precisa (`fetch`): o A de
registro.br, a DNSKEY de registro.br, o DS de registro.br em .br, a DNSKEY de .br, o DS de .br
na raiz e a DNSKEY da raiz. Depois ele **sobe** conferindo: a DNSKEY da raiz é validada pela
âncora **38696, a KSK-2024** (`verify rdataset (keyid=38696): success`). Em seguida:
a ZSK da raiz (8763) assina o DS de .br; esse DS garante as chaves de .br, que são assinadas
pela chave 38298 de .br; a chave 32480 de .br assina o DS de registro.br; esse DS garante as
chaves de registro.br; e a chave 59973 de registro.br assina tanto o próprio conjunto de chaves
quanto o registro A.

Cada elo termina em `marking as secure`, e no fim aparece **`fully validated`**: o IP
200.160.2.3 está ligado à raiz por uma corrente de assinaturas sem nenhum elo quebrado.

Dois detalhes da saída:
- `no RRSIG matching DS key` na raiz não é erro. A raiz tem duas KSKs na âncora, mas assina o
  conjunto de chaves só com a 38696, então a 20326 não tem assinatura correspondente. Basta uma
  chave da âncora validar.
- O TTL aparece como 300, e não 172800 (o TTL original no RRSIG), porque o `cache 300` da
  borda limita o tempo que as respostas ficam guardadas.

## Prints para o vídeo (sugestão, Jamily)

A issue não pede prints, mas, se quiser mostrar este módulo no vídeo, os melhores são:

1. O `lab.ds` ao lado do resultado do `dnssec-dsfromkey`, mostrando que os dois resumos são iguais.
2. A linha da 38696 com `[  VALID  ]` no `root.key` do contêiner.
3. O fim do `delv +vtrace`: as linhas `verify rdataset (keyid=38696): success` e `fully validated`.

## Resumo

| Item do checklist | Situação |
| --- | --- |
| Mostrar o DS em `lab.ds` e explicar o papel dele | Ok, com prova de que é o resumo da KSK 50164 |
| Mostrar a KSK-2024 (38696) no `root.key` | Ok, no arquivo e marcada `VALID` pelo Unbound |
| `delv @172.21.0.53 registro.br +vtrace` com `fully validated` | Ok |
