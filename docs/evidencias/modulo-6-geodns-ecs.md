# Issue #8: Módulo 6 — GeoDNS e ECS

Data: 27/11/2026.
Ambiente: Windows 11, PowerShell no VS Code, Docker Desktop com WSL 2.

## 1. Configuração do GeoDNS no `borda/Corefile`

O arquivo `borda/Corefile` configura o GeoDNS por meio de três blocos `geo.internal:53`.

O plugin `view` permite selecionar uma configuração de acordo com uma expressão:

- `view regiao-a`: identifica consultas originadas na rede `172.21.0.0/24`.
- `view regiao-b`: identifica consultas originadas na rede `172.22.0.0/24`.
- `client_ip()`: obtém o endereço IP de origem da consulta.
- `incidr()`: verifica se o endereço IP pertence ao prefixo de rede informado.
- `hosts`: associa o domínio `cdn.geo.internal` ao endereço IP correspondente.

As respostas configuradas são:

- Região A: `10.1.0.10`.
- Região B: `10.2.0.10`.
- Demais clientes: `10.0.0.10`.

**Observação:** a configuração original do `borda/Corefile` foi analisada sem alterações.

## 2. Teste do GeoDNS

**Cliente A**

Comando executado:

```powershell
docker compose exec cliente-a bash -c "dig @172.21.0.53 cdn.geo.internal +short"
```

Resultado:

```text
10.1.0.10
```

**Cliente B**

Comando executado:

```powershell
docker compose exec cliente-b bash -c "dig @172.22.0.53 cdn.geo.internal +short"
```

Resultado:

```text
10.2.0.10
```

Os resultados demonstram que o mesmo domínio retorna endereços IP diferentes conforme a rede de origem da consulta DNS.

## 3. ECS — EDNS Client Subnet (RFC 7871)

O ECS é uma extensão do DNS que permite compartilhar parte do prefixo de rede do cliente por meio de uma opção EDNS. Essa informação pode auxiliar servidores DNS autoritativos a fornecer respostas geograficamente mais próximas do usuário, como na seleção de servidores de CDNs.

Apesar desse benefício, o ECS possui implicações de privacidade, pois compartilha informações sobre a rede do cliente.

**Diferença em relação ao laboratório:** a implementação apresentada utiliza o plugin `view` do CoreDNS, que seleciona as respostas com base no endereço IP de origem da consulta. O laboratório não implementa o mecanismo ECS.

## 4. Como explicar no vídeo

O GeoDNS permite que um mesmo domínio retorne endereços IP diferentes conforme a rede de origem do cliente. No laboratório, o CoreDNS utiliza o plugin `view` para identificar a rede por meio do IP de origem e selecionar a resposta correspondente. O teste mostrou que o cliente A recebeu `10.1.0.10`, enquanto o cliente B recebeu `10.2.0.10`. Também foi documentado o ECS, definido pela RFC 7871, que permite compartilhar parte do prefixo de rede do cliente para auxiliar na escolha de respostas geograficamente próximas. Esse mecanismo é diferente do `view` utilizado no laboratório.
