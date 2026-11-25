#!/usr/bin/env bash
# Simula um atacante: troca o IP de banco.lab.internal DEPOIS da assinatura.
# O RRSIG continua sendo o da resposta original, então não confere mais.
# Rode dentro do cliente-a:  bash /lab/scripts/quebrar_zona.sh
set -euo pipefail

LAB="${LAB:-/lab}"
ARQ="$LAB/autoritativo/zonas/db.lab.internal.signed"

# 1) troca o IP sem reassinar
sed -i 's/10\.0\.0\.43/10.6.6.6/' "$ARQ"

# 2) aumenta o serial em 1 para o autoritativo recarregar a zona
awk '!feito && /; serial/ { sub($1, $1 + 1); feito = 1 } { print }' "$ARQ" > "$ARQ.tmp"
cat "$ARQ.tmp" > "$ARQ" && rm -f "$ARQ.tmp"

echo "banco.lab.internal agora aponta para 10.6.6.6, com a assinatura antiga."
echo "Espere uns 6 segundos (o autoritativo recarrega a zona) e consulte:"
echo "  dig @172.21.0.53 banco.lab.internal +dnssec"
