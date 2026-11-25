"""Resume as medições e gera os gráficos.

Rode dentro do cliente-a, depois do medir.py:  python3 /lab/medicao/analisar.py
Gera: medicao/dados/resumo.csv, mediana_por_protocolo.png e cache_frio_quente.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # gera arquivos de imagem sem precisar de tela
import matplotlib.pyplot as plt
import pandas as pd

DADOS = Path(__file__).parent / "dados"
ORDEM = ["udp", "dot", "doh_nova", "doh_reuso"]
NOMES_PROTO = {"udp": "UDP", "dot": "DoT", "doh_nova": "DoH (conexão nova)", "doh_reuso": "DoH (conexão reaproveitada)"}

df = pd.read_csv(DADOS / "medicoes.csv")
falhas = df[~df.ok].groupby(["alvo", "protocolo"]).size()
if len(falhas):
    print("Consultas que falharam (por alvo e protocolo):")
    print(falhas.to_string(), "\n")
df = df[df.ok]

# Resumo: mediana e percentil 95 (a média engana quando há consultas lentas isoladas)
resumo = (
    df.groupby(["alvo", "protocolo"])["ms"]
      .agg(medicoes="count", mediana="median", p95=lambda s: s.quantile(0.95))
      .round(1)
)
print(resumo.to_string())
resumo.to_csv(DADOS / "resumo.csv")

# Gráfico 1: mediana por alvo, uma barra por protocolo
med = df.groupby(["alvo", "protocolo"])["ms"].median().unstack()
med = med[[p for p in ORDEM if p in med.columns]].rename(columns=NOMES_PROTO)
ax = med.plot.bar(figsize=(10, 5.5), rot=0, width=0.8,
                  color=["#9aa5b1", "#5B3FA0", "#E07A2F", "#2E8B57"])
ax.set_ylabel("latência mediana (ms)")
ax.set_xlabel("")
ax.set_title("Quanto custa cifrar o DNS? Latência mediana por resolvedor e protocolo")
ax.grid(axis="y", alpha=0.3)
ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.07))
for barras in ax.containers:
    ax.bar_label(barras, fmt="%.0f", fontsize=8, padding=2)
plt.tight_layout()
plt.savefig(DADOS / "mediana_por_protocolo.png", dpi=150)
plt.close()

# Gráfico 2: cache frio x quente no resolvedor local (cada nome perguntado duas vezes)
arq_cache = DADOS / "cache.csv"
if arq_cache.exists():
    cache = pd.read_csv(arq_cache)
    print("\nCache (mediana em ms):")
    print(cache.groupby("cache")["ms"].median().round(1).to_string())
    pares = cache.pivot(index="nome", columns="cache", values="ms").dropna()
    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(pares))
    ax.bar([i - 0.2 for i in x], pares["frio"], width=0.4, label="1ª consulta (cache frio)", color="#9aa5b1")
    ax.bar([i + 0.2 for i in x], pares["quente"], width=0.4, label="2ª consulta (cache quente)", color="#5B3FA0")
    ax.set_xticks(list(x))
    ax.set_xticklabels(pares.index, rotation=30, ha="right")
    ax.set_ylabel("latência (ms)")
    ax.set_title("O cache em ação: a mesma pergunta, duas vezes seguidas")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(DADOS / "cache_frio_quente.png", dpi=150)
    plt.close()

print(f"\nGráficos salvos em {DADOS}")
