# Issue #1: Subir o laboratório com Docker

Máquina: Windows 11 Home, PowerShell no VS Code, Docker Desktop (servidor 29.9.3, WSL 2).
Data: 26/11/2026.

## 0. Problema encontrado antes de começar e como foi resolvido

O `docker info` mostrava só a parte `Client:` e terminava com:

```
Server:
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

E os serviços do Windows estavam assim:

```
Name               Status  StartType
com.docker.service Stopped Manual
vmcompute          Stopped Disabled
WSLService         Running Automatic
```

O serviço `vmcompute` (Host Compute Service do Hyper-V) estava desativado. É ele que cria a
máquina virtual leve onde o WSL 2 e o Docker rodam, por isso aparecia o erro
`HCS_E_SERVICE_NOT_AVAILABLE` ("HCS" é justamente Host Compute Service). A virtualização na
BIOS já estava ativa (`VirtualizationFirmwareEnabled: True`).

Solução, no PowerShell como Administrador:

```powershell
Set-Service vmcompute -StartupType Manual
Start-Service vmcompute
```

Depois disso, o Docker Desktop abriu e o `docker info` passou a mostrar a seção `Server`.

## 1. Instalar Docker Desktop, Git e Wireshark

```powershell
docker info --format '{{.ServerVersion}} {{.OperatingSystem}}'
git --version
docker compose version
```

```
29.9.3 Docker Desktop
git version 2.55.0.windows.2
Docker Compose version v5.7.1
```

Docker e Git estão instalados e funcionando. **O Wireshark não foi encontrado** em
`C:\Program Files\Wireshark\`.

> **Pendente (Jamily):** instalar o Wireshark em https://www.wireshark.org/download.html
> (instalador Windows x64, aceitar a instalação do Npcap). Ele vai ser usado nas issues #5 e #6
> para abrir os arquivos `.pcap` da pasta `capturas/`.

## 2. `docker compose build`

```powershell
docker compose build
```

Final da saída:

```
#19 naming to docker.io/library/lab-dns-moderno-cliente-b:latest 0.0s done
#19 DONE 20.7s
#20 naming to docker.io/library/lab-dns-moderno-cliente-a:latest 0.0s done
#20 DONE 20.7s
 Image lab-dns-moderno-cliente-a Built
 Image lab-dns-moderno-cliente-b Built
 Image lab-dns-moderno-resolvedor Built
```

As três imagens que o projeto constrói (os dois clientes e o resolvedor Unbound) foram criadas
sem erro. O `autoritativo` e a `borda` não aparecem aqui porque usam a imagem pronta
`coredns/coredns:1.12.1`, que é baixada no `up`.

## 3. `docker compose run --rm cliente-a bash /lab/scripts/preparar.sh`

```powershell
docker compose run --rm cliente-a bash /lab/scripts/preparar.sh
```

```
 Container lab-dns-moderno-cliente-a-run-1cb347bb00a6 Creating
 Container lab-dns-moderno-cliente-a-run-1cb347bb00a6 Created
Gerando as chaves...
Zona assinada: autoritativo/zonas/db.lab.internal.signed
Âncora (DS da KSK) em resolvedor/lab.ds:
lab.internal. IN DS 50164 13 2 9F06239062AA746FF2C9F3CE41951014D3676E082685FD2CF0BE0D11356B2FBA

Certificado criado em borda/certs/

Pronto. Agora rode: docker compose up -d
```

O script gerou duas chaves (a KSK, de tag 50164, e a ZSK, de tag 30805), assinou a zona
`lab.internal` e criou o DS da KSK em `resolvedor/lab.ds`, que é a "âncora de confiança" do
resolvedor. O `13` no DS é o algoritmo ECDSA P-256 com SHA-256 e o `2` é o tipo de resumo
(SHA-256). Também foi criado o certificado autoassinado do DoT/DoH.

> Observação: se esse comando for rodado pelo **Git Bash**, ele falha com
> `bash: C:/Program Files/Git/lab/scripts/preparar.sh: No such file or directory`, porque o
> Git Bash converte caminhos que começam com `/`. No PowerShell funciona normalmente. No Git
> Bash, use `MSYS_NO_PATHCONV=1 docker compose run ...` ou `//lab/scripts/preparar.sh`.

Os arquivos gerados ficam fora do Git, como manda o `.gitignore` (`git status --ignored`):

```
!! autoritativo/zonas/Klab.internal.+013+30805.key
!! autoritativo/zonas/Klab.internal.+013+30805.private
!! autoritativo/zonas/Klab.internal.+013+50164.key
!! autoritativo/zonas/Klab.internal.+013+50164.private
!! autoritativo/zonas/db.lab.internal.signed
!! autoritativo/zonas/dsset-lab.internal.
!! borda/certs/cert.pem
!! borda/certs/key.pem
!! resolvedor/lab.ds
```

## 4. `docker compose up -d` e `docker compose ps`

```powershell
docker compose up -d
docker compose ps
```

Final da saída do `up` (antes disso ele baixou a imagem do CoreDNS):

```
 Image coredns/coredns:1.12.1 Pulled
 Network lab-dns-moderno_core Created
 Network lab-dns-moderno_regiao_b Created
 Container lab-dns-moderno-autoritativo-1 Started
 Container lab-dns-moderno-resolvedor-1 Started
 Container lab-dns-moderno-borda-1 Started
 Container lab-dns-moderno-cliente-a-1 Started
 Container lab-dns-moderno-cliente-b-1 Started
```

`docker compose ps`, cerca de 20 segundos depois:

```
SERVICE        STATE     STATUS
autoritativo   running   Up 20 seconds
borda          running   Up 19 seconds
cliente-a      running   Up 20 seconds
cliente-b      running   Up 20 seconds
resolvedor     running   Up 20 seconds
```

Os cinco contêineres estão `running` e continuam de pé depois de alguns segundos, o que mostra
que o `resolvedor` e a `borda` encontraram o `lab.ds` e os certificados (sem eles, os dois
apareceriam como "Exited").

## 5. Teste extra: o laboratório responde de verdade

```powershell
docker compose exec -T cliente-a dig "@172.21.0.53" www.lab.internal +dnssec +noall +comments +answer
```

```
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 59766
;; flags: qr rd ra ad; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags: do; udp: 1232
; COOKIE: e84a16049bab9786 (echoed)
;; ANSWER SECTION:
www.lab.internal.	300	IN	A	10.0.0.80
www.lab.internal.	300	IN	RRSIG	A 13 3 300 20271126234257 20261126234257 30805 lab.internal. N03D9M/1XqNIWXO5MTmjDC8D4Cm4Gygd6+LCqw/gU3CjhDzp5k1ScA20 McCzA3o+/8dm6Ak4fyEa7WmxGmtG4w==
```

Logs gerados por essa consulta (`docker compose logs`):

```
borda-1         | [INFO] 172.21.0.100:38020 - 59766 "A IN www.lab.internal. udp 57 true 1232" NOERROR qr,rd,ra,ad 192 0.003364802s
autoritativo-1  | [INFO] 172.20.0.20:25296 - 49016 "A IN www.lab.internal. udp 45 true 1232" NOERROR qr,aa,cd 356 0.000198862s
autoritativo-1  | [INFO] 172.20.0.20:55659 - 32053 "DNSKEY IN lab.internal. udp 41 true 1232" NOERROR qr,aa,cd 626 0.00026237s
```

A consulta saiu do `cliente-a` (172.21.0.100), passou pela `borda`, que repassou ao
`resolvedor` (172.20.0.20), que perguntou ao `autoritativo` tanto o registro A quanto as chaves
DNSKEY. A flag `ad` (Authenticated Data) na resposta mostra que o Unbound conseguiu validar a
assinatura RRSIG com a âncora do `lab.ds`, ou seja, a cadeia toda funciona.

## Resumo

| Item do checklist | Situação |
| --- | --- |
| Instalar Docker Desktop, Git e Wireshark | Docker e Git ok. **Wireshark pendente** |
| `docker compose build` | Ok |
| `preparar.sh` | Ok (no PowerShell) |
| `up -d` com 5 contêineres running | Ok |
| Anotar erros e solução | Feito nesta página e em comentário na issue |
