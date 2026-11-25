"""Mede a latência de consultas DNS por UDP, DoT e DoH.

Compara a borda do laboratório com três resolvedores públicos anycast.
Rode dentro do cliente-a:  python3 /lab/medicao/medir.py
Gera: medicao/dados/medicoes.csv e medicao/dados/cache.csv

Antes de rodar, reinicie a borda e o resolvedor para esvaziar os caches:
  docker compose restart borda resolvedor
"""
import csv
import os
import random
import ssl
import time
from pathlib import Path

import dns.message
import dns.query
import dns.rdatatype
import httpx

LOCAL = os.environ.get("BORDA", "172.21.0.53")

# nome: (ip, nome no certificado, url do DoH)
ALVOS = {
    "local":      (LOCAL,     None,                 f"https://{LOCAL}/dns-query"),
    "cloudflare": ("1.1.1.1", "cloudflare-dns.com", "https://cloudflare-dns.com/dns-query"),
    "google":     ("8.8.8.8", "dns.google",         "https://dns.google/dns-query"),
    "quad9":      ("9.9.9.9", "dns.quad9.net",      "https://dns.quad9.net/dns-query"),
}
PROTOCOLOS = ["udp", "dot", "doh_nova", "doh_reuso"]
NOMES = ["ufal.br", "gov.br", "registro.br", "wikipedia.org", "github.com"]
RODADAS = int(os.environ.get("RODADAS", "30"))
PAUSA = 0.2  # segundos entre consultas, para não sobrecarregar os servidores públicos

# Nomes usados SÓ no teste de cache (não aparecem em mais nenhum lugar)
NOMES_CACHE = ["usp.br", "unicamp.br", "ufpe.br", "ufba.br", "ufrn.br",
               "ufc.br", "ufmg.br", "unb.br", "ufrj.br", "ufpb.br"]

SAIDA = Path(__file__).parent / "dados" / "medicoes.csv"
SAIDA_CACHE = Path(__file__).parent / "dados" / "cache.csv"

# O certificado da borda é autoassinado: no laboratório, aceitamos sem verificar
sem_verificar = ssl.create_default_context()
sem_verificar.check_hostname = False
sem_verificar.verify_mode = ssl.CERT_NONE

# Uma conexão HTTP/2 aberta por alvo, reaproveitada no "doh_reuso"
sessoes = {a: httpx.Client(http2=True, verify=(a != "local")) for a in ALVOS}


def medir(alvo, protocolo, nome):
    ip, sni, url = ALVOS[alvo]
    q = dns.message.make_query(nome, dns.rdatatype.A)
    t0 = time.perf_counter()
    if protocolo == "udp":
        dns.query.udp(q, ip, timeout=3)
    elif protocolo == "dot":  # conexão TLS nova a cada consulta
        ctx = sem_verificar if alvo == "local" else ssl.create_default_context()
        dns.query.tls(q, ip, timeout=3, ssl_context=ctx, server_hostname=sni)
    elif protocolo == "doh_nova":  # conexão HTTPS nova a cada consulta
        dns.query.https(q, url, timeout=3, verify=(alvo != "local"))
    else:  # doh_reuso: a mesma conexão para todas as consultas
        dns.query.https(q, url, timeout=3, session=sessoes[alvo])
    return (time.perf_counter() - t0) * 1000


def medir_cache():
    """Pergunta cada nome duas vezes à borda: a 1ª vai até a internet (cache frio),
    a 2ª vem da memória (cache quente)."""
    with open(SAIDA_CACHE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nome", "cache", "ms"])
        for nome in NOMES_CACHE:
            for cache in ["frio", "quente"]:
                try:
                    w.writerow([nome, cache, round(medir("local", "udp", nome), 2)])
                except Exception:
                    pass
                time.sleep(PAUSA)
    print(f"Teste de cache salvo em {SAIDA_CACHE}")


def main():
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    medir_cache()
    total = RODADAS * len(ALVOS) * len(PROTOCOLOS) * len(NOMES)
    feitas = 0
    with open(SAIDA, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rodada", "alvo", "protocolo", "nome", "ms", "ok"])
        for rodada in range(RODADAS):
            combos = [(a, p, n) for a in ALVOS for p in PROTOCOLOS for n in NOMES]
            random.shuffle(combos)  # nenhum alvo fica sempre no mesmo momento da rodada
            for alvo, protocolo, nome in combos:
                try:
                    ms = medir(alvo, protocolo, nome)
                    w.writerow([rodada, alvo, protocolo, nome, round(ms, 2), True])
                except Exception:
                    w.writerow([rodada, alvo, protocolo, nome, "", False])
                feitas += 1
                time.sleep(PAUSA)
            print(f"rodada {rodada + 1}/{RODADAS} concluída ({feitas}/{total} consultas)")
    print(f"Dados salvos em {SAIDA}")


if __name__ == "__main__":
    main()
