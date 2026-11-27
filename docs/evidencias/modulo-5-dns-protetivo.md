# Issue #7: Módulo 5, DNS protetivo e domínio canário

Máquina: Windows 11 Home, PowerShell, Docker Desktop 29.9.3.
Data: 27/11/2026 (horário dos contêineres em UTC).

Os comandos foram rodados dentro do `cliente-a` (`docker compose exec cliente-a bash`).

## Como funciona (para ler antes das saídas)

**DNS protetivo** é usar o próprio resolvedor como filtro: se o nome está numa lista de
bloqueio, o resolvedor responde um endereço que não leva a lugar nenhum (`0.0.0.0`) em vez do
endereço verdadeiro. O navegador nem chega a abrir a conexão com o site de anúncio, malware ou
phishing. Empresas, escolas e serviços como o Quad9 fazem isso.

No laboratório, quem filtra é a **borda** (CoreDNS), com o plugin `hosts` lendo
`borda/bloqueio.hosts`:

```
# Lista de bloqueio do DNS protetivo (formato hosts)
# O CoreDNS relê este arquivo a cada 2 s: dá para bloquear ou liberar ao vivo.

0.0.0.0 phishing-banco.lab.internal
0.0.0.0 malware.lab.internal
0.0.0.0 doubleclick.net
```

No `borda/Corefile`, esse bloqueio fica no trecho `(resolver)`, que é importado pelos três
protocolos (DNS comum na 53, DoT na 853 e DoH na 443). No CoreDNS, quem decide a ordem dos
plugins é o próprio CoreDNS, e não a ordem das linhas no arquivo: o `cache` é consultado
primeiro e, se a resposta não estiver guardada, a pergunta passa pelo `hosts`. O `fallthrough`
faz os nomes que **não** estão na lista seguirem para o Unbound normalmente.

## 1. `doubleclick.net` respondendo 0.0.0.0 pela borda

```bash
dig @172.21.0.53 doubleclick.net
```

```
; <<>> DiG 9.18.49-1~deb12u3-Debian <<>> @172.21.0.53 doubleclick.net
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 2404
;; flags: qr aa rd; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
;; WARNING: recursion requested but not available

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1232
; COOKIE: 35349780654bf813 (echoed)
;; QUESTION SECTION:
;doubleclick.net.		IN	A

;; ANSWER SECTION:
doubleclick.net.	10	IN	A	0.0.0.0

;; Query time: 3 msec
;; SERVER: 172.21.0.53#53(172.21.0.53) (UDP)
;; WHEN: Fri Nov 27 01:29:11 UTC 2026
;; MSG SIZE  rcvd: 87
```

A borda respondeu **`0.0.0.0`**, um endereço que não pertence a nenhuma máquina. A resposta não
é um erro (`status: NOERROR`), é uma resposta "inventada". As pistas de que ela foi criada na
própria borda, sem consultar a internet, são: a flag `aa` (a borda se declara "dona" da
resposta), a falta da flag `ra` (por isso o aviso `recursion requested but not available`) e o
TTL **10**, que é o `ttl 10` do Corefile. Um TTL curto faz um desbloqueio valer rápido.

### O mesmo bloqueio vale para DoT e DoH

```bash
dig @172.21.0.53 +tls doubleclick.net +short
dig @172.21.0.53 +https doubleclick.net +short
dig @172.21.0.53 +https malware.lab.internal +short
```

```
0.0.0.0
0.0.0.0
0.0.0.0
```

Como os três protocolos importam o mesmo trecho `(resolver)`, o bloqueio vale igual por DNS
comum, DoT e DoH. O DoT e o DoH protegem o caminho até a borda, mas quem decide a resposta
continua sendo a borda.

O log da borda mostra as quatro consultas bloqueadas:

```powershell
docker compose logs --since 5m borda | grep -E "doubleclick|use-application|malware"
```

```
borda-1  | [INFO] 172.21.0.100:60912 - 2404 "A IN doubleclick.net. udp 56 false 1232" NOERROR qr,aa,rd 64 0.002247547s
borda-1  | [INFO] 172.21.0.100:38759 - 64320 "A IN doubleclick.net. tcp 56 false 65535" NOERROR qr,aa,rd 64 0.000239929s
borda-1  | [INFO] 172.21.0.100:45885 - 2100 "A IN doubleclick.net. tcp 56 false 65535" NOERROR qr,aa,rd 64 0.000066835s
borda-1  | [INFO] 172.21.0.100:34297 - 22583 "A IN malware.lab.internal. tcp 61 false 65535" NOERROR qr,aa,rd 74 0.000055333s
borda-1  | [INFO] 172.21.0.100:39384 - 28828 "A IN use-application-dns.net. udp 64 false 1232" NXDOMAIN qr,aa,rd 41 0.000778387s
borda-1  | [INFO] 172.21.0.100:34646 - 19736 "AAAA IN use-application-dns.net. udp 64 false 1232" NXDOMAIN qr,aa,rd 41 0.000201487s
```

A primeira linha é a consulta por UDP (o ID 2404 é o mesmo do `dig` acima). As três seguintes
são o DoT e os dois DoH, que o log registra como `tcp`, porque os dois rodam sobre TCP. Todas
têm `aa` e levam frações de milissegundo: a borda respondeu da lista, sem perguntar a ninguém.
As duas últimas linhas são do domínio canário, na seção 3.

## 2. O mesmo nome passando por `@1.1.1.1` (limite do DNS protetivo)

```bash
dig @1.1.1.1 doubleclick.net +time=3 +tries=1
```

```
; <<>> DiG 9.18.49-1~deb12u3-Debian <<>> @1.1.1.1 doubleclick.net +time=3 +tries=1
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 28671
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1232
;; QUESTION SECTION:
;doubleclick.net.		IN	A

;; ANSWER SECTION:
doubleclick.net.	275	IN	A	142.251.132.238

;; Query time: 55 msec
;; SERVER: 1.1.1.1#53(1.1.1.1) (UDP)
;; WHEN: Fri Nov 27 01:29:11 UTC 2026
;; MSG SIZE  rcvd: 60
```

Perguntando direto a outro resolvedor (o 1.1.1.1, da Cloudflare), o mesmo nome voltou com o
**endereço verdadeiro**, 142.251.132.238, e a flag `ra` de uma resposta recursiva normal. A
consulta nem passou pela borda, então a lista de bloqueio não teve como agir.

Esse é o **limite do DNS protetivo**: ele só protege quem usa aquele resolvedor. Um programa
(ou um malware) que escolhe outro resolvedor, ou que usa DoH direto para um servidor de fora,
escapa do filtro. Para fechar essa porta, uma rede precisaria também bloquear o DNS de saída
para outros servidores, e mesmo assim o DoH na porta 443 se confunde com navegação comum
(issue #6).

## 3. `use-application-dns.net` com NXDOMAIN

```bash
dig @172.21.0.53 use-application-dns.net
```

```
; <<>> DiG 9.18.49-1~deb12u3-Debian <<>> @172.21.0.53 use-application-dns.net
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NXDOMAIN, id: 28828
;; flags: qr aa rd; QUERY: 1, ANSWER: 0, AUTHORITY: 0, ADDITIONAL: 1
;; WARNING: recursion requested but not available

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 1232
; COOKIE: a7d9883d5a417798 (echoed)
;; QUESTION SECTION:
;use-application-dns.net.	IN	A

;; Query time: 0 msec
;; SERVER: 172.21.0.53#53(172.21.0.53) (UDP)
;; WHEN: Fri Nov 27 01:29:11 UTC 2026
;; MSG SIZE  rcvd: 64
```

Também para o tipo AAAA (IPv6):

```bash
dig @172.21.0.53 use-application-dns.net AAAA +noall +comments | grep status
```

```
;; ->>HEADER<<- opcode: QUERY, status: NXDOMAIN, id: 19736
```

E, para comparar, o mesmo nome perguntado ao 1.1.1.1:

```bash
dig @1.1.1.1 use-application-dns.net +noall +comments +answer | grep -E 'status|flags|IN'
```

```
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 56327
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1
; EDNS: version: 0, flags:; udp: 1232
use-application-dns.net. 81569	IN	A	35.190.14.201
```

`use-application-dns.net` é o **domínio canário** do Firefox. Antes de ligar sozinho o DoH
para um resolvedor de fora, o Firefox pergunta esse nome ao DNS da rede. Se a resposta for
**NXDOMAIN** ("esse nome não existe"), ele entende que a rede está pedindo para não ligar o DoH
automático, e continua usando o DNS da rede. A borda faz isso com o plugin `template`, que
responde NXDOMAIN para qualquer tipo de pergunta (por isso deu NXDOMAIN em A e em AAAA). Na
internet aberta, pelo 1.1.1.1, o nome existe (`NOERROR`, 35.190.14.201), então lá o Firefox
seguiria em frente.

Isso junta as seções 1 e 2: o canário é a forma de a rede dizer "não fuja do meu DNS
protetivo pelo DoH". Mas é só um **pedido**: vale para o DoH automático do Firefox, e não
impede quem liga o DoH na mão, nem outros programas.

## Prints para o vídeo (opcional, Jamily)

A issue não pede prints. Se quiser mostrar este módulo no vídeo, os mais claros são:

1. O `dig @172.21.0.53 doubleclick.net +short` (0.0.0.0) e o `dig @1.1.1.1 doubleclick.net +short`
   (IP verdadeiro), um embaixo do outro. É o bloqueio e o limite dele numa imagem só.
2. O `dig @172.21.0.53 use-application-dns.net` com `status: NXDOMAIN` em destaque.

## Resumo

| Item do checklist | Situação |
| --- | --- |
| `doubleclick.net` respondendo 0.0.0.0 pela borda | Ok, também por DoT e DoH |
| O mesmo nome passando por `@1.1.1.1` | Ok, voltou o IP verdadeiro 142.251.132.238 |
| `use-application-dns.net` com NXDOMAIN | Ok, em A e AAAA, com o contraste do 1.1.1.1 (NOERROR) |

## Como explicar no vídeo

Sugestão de fala:

> O DNS protetivo usa o resolvedor como filtro. Se o nome está na lista de bloqueio, a borda
> responde 0.0.0.0, um endereço que não leva a lugar nenhum, e o navegador nem chega a abrir o
> site de anúncio ou de golpe. Como a lista de bloqueio está no trecho de configuração comum aos
> três protocolos, e é aplicada antes de a pergunta seguir para o Unbound, ela vale igual para
> UDP, DoT e DoH.
>
> Mas tem um limite: ele só protege quem pergunta para esse resolvedor. Perguntando direto ao
> 1.1.1.1, o mesmo nome volta com o IP verdadeiro.
>
> É aí que entra o domínio canário. Antes de ligar o DoH sozinho, o Firefox pergunta
> `use-application-dns.net` à rede. A nossa borda responde que o nome não existe, e o Firefox
> entende que a rede pede para ele não fugir do DNS dela. Na internet aberta, esse nome existe.
> Mas é só um pedido: quem liga o DoH na mão, ou outro programa, ainda escapa.

O que mostrar na tela: o `dig` pela borda (0.0.0.0) e pelo 1.1.1.1 (o IP verdadeiro), um embaixo
do outro, e o `NXDOMAIN` do domínio canário.
