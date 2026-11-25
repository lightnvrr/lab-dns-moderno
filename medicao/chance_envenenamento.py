"""Quantas tentativas um atacante precisa para envenenar um cache DNS?

Nenhum pacote é enviado: é só a conta, para comparar
um resolvedor antigo (só o ID é aleatório) com um moderno (ID + porta de origem).
"""
import math

N = 1000  # respostas falsas que o atacante consegue mandar antes de a verdadeira chegar

cenarios = {
    "Só o ID aleatório (16 bits)": 2**16,
    "ID + porta de origem (cerca de 32 bits)": 2**32,
}

print(f"Atacante com {N} respostas falsas por tentativa (\"corrida\"):\n")
for nome, espaco in cenarios.items():
    p = N / espaco                                          # chance de vencer uma corrida
    corridas = math.ceil(math.log(0.5) / math.log(1 - p))   # corridas para 50% de chance
    print(f"{nome}")
    print(f"  combinações possíveis:       {espaco:>15,}".replace(",", "."))
    print(f"  chance por corrida:          {p:>15.7f}")
    print(f"  corridas para 50% de chance: {corridas:>15,}".replace(",", "."))
    print()

print("Com o truque de Kaminsky (2008), cada nome inventado começa uma corrida nova.")
print("Dezenas de corridas levam segundos; milhões já não. A garantia de verdade vem do DNSSEC.")
