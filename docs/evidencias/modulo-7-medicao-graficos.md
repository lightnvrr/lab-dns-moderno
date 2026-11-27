# Issue #9: Módulo 7 — medição e gráficos

Data: 27/11/2026.  
Ambiente: Windows 11, PowerShell no VS Code, Docker Desktop com WSL 2.

## 1. Preparação do ambiente

Foi verificado que os cinco contêineres do laboratório estavam ativos.

Em seguida, os contêineres `borda` e `resolvedor` foram reiniciados para esvaziar os caches antes da medição:

```powershell
docker compose restart borda resolvedor
```

## 2. Teste rápido

Foi executado um teste inicial com três rodadas:

```powershell
docker compose exec -e RODADAS=3 cliente-a python3 /lab/medicao/medir.py
```

Resultado:

```text
rodada 1/3 concluída (80/240 consultas)
rodada 2/3 concluída (160/240 consultas)
rodada 3/3 concluída (240/240 consultas)
Dados salvos em /lab/medicao/dados/medicoes.csv
```

A verificação do CSV confirmou:

```text
True   240
```

As 240 consultas foram bem-sucedidas, sem falhas.

Cada uma das 16 combinações de alvo e protocolo apresentou 15 medições, conforme esperado.

## 3. Identificação dos resolvedores públicos

Foram consultados os registros `id.server` dos resolvedores Cloudflare e Quad9:

```powershell
docker compose exec cliente-a bash -c "dig @1.1.1.1 id.server CH TXT +short"
docker compose exec cliente-a bash -c "dig @9.9.9.9 id.server CH TXT +short"
```

Resultados:

| Resolvedor | Endereço | Identificador |
|---|---|---|
| Cloudflare | 1.1.1.1 | `for01` |
| Quad9 | 9.9.9.9 | `res700.qfor1` |

## 4. Medição completa

Após a aprovação do teste rápido, foi executada a medição com as 30 rodadas previstas:

```powershell
docker compose exec cliente-a python3 /lab/medicao/medir.py
```

O script comparou quatro alvos:

- Borda local;
- Cloudflare;
- Google;
- Quad9.

Foram utilizados quatro protocolos:

- UDP;
- DoT;
- DoH com conexão nova;
- DoH com conexão reaproveitada.

Cada rodada realizou 80 consultas, totalizando 2.400 consultas principais.

Resultado:

```text
rodada 30/30 concluída (2400/2400 consultas)
Dados salvos em /lab/medicao/dados/medicoes.csv
```

A verificação do arquivo confirmou:

```text
True  2400
```

Portanto, todas as 2.400 consultas foram bem-sucedidas.

Cada combinação de alvo e protocolo apresentou 150 medições válidas.

## 5. Análise dos resultados

Foi executado o script de análise:

```powershell
docker compose exec cliente-a python3 /lab/medicao/analisar.py
```

O script calculou a quantidade de medições, a mediana e o percentil 95 (P95) de cada combinação.

### Resultados obtidos

| Alvo | Protocolo | Mediana (ms) | P95 (ms) |
|---|---|---:|---:|
| Local | UDP | 1,4 | 2,5 |
| Local | DoT | 47,1 | 50,2 |
| Local | DoH nova | 7,0 | 61,2 |
| Local | DoH reuso | 3,9 | 8,6 |
| Cloudflare | UDP | 65,1 | 66,6 |
| Cloudflare | DoT | 100,1 | 143,2 |
| Cloudflare | DoH nova | 106,9 | 219,7 |
| Cloudflare | DoH reuso | 27,4 | 120,5 |
| Google | UDP | 47,2 | 89,6 |
| Google | DoT | 220,0 | 249,6 |
| Google | DoH nova | 224,5 | 265,9 |
| Google | DoH reuso | 51,5 | 207,0 |
| Quad9 | UDP | 22,7 | 23,7 |
| Quad9 | DoT | 100,2 | 104,4 |
| Quad9 | DoH nova | 103,1 | 113,4 |
| Quad9 | DoH reuso | 23,4 | 78,7 |

### Observações

- A borda local apresentou as menores medianas de latência, especialmente com UDP (1,4 ms).
- Entre os resolvedores públicos, o Quad9 apresentou a menor mediana no UDP (22,7 ms).
- O reaproveitamento da conexão DoH apresentou medianas menores que o DoH com conexão nova nos quatro alvos.
- O Google apresentou as maiores medianas em DoT e DoH com conexão nova.
- O P95 permite observar o comportamento das consultas mais lentas, complementando a análise da mediana.

## 6. Análise do cache

O teste de cache foi realizado com dez domínios, consultando cada um duas vezes: primeiro com cache frio e depois com cache quente.

O arquivo `cache.csv` contém 20 registros.

Resultado das medianas:

```text
Cache
frio      1.5
quente    1.5
```

As medianas foram iguais, ambas de 1,5 ms. Portanto, nessa execução, não foi observada diferença na mediana entre as consultas com cache frio e quente.

## 7. Arquivos gerados

Os arquivos foram salvos em `medicao/dados/`:

- `medicoes