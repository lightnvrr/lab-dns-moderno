#!/usr/bin/env bash
# Gera as chaves (se ainda não existirem), assina a zona lab.internal
# e cria o DS da KSK, que vira a âncora de confiança do resolvedor.
# Rode dentro do cliente-a:  bash /lab/scripts/assinar_zona.sh
set -euo pipefail

LAB="${LAB:-/lab}"
ZONA=lab.internal
cd "$LAB/autoritativo/zonas"

if ! ls K${ZONA}.+013+*.key >/dev/null 2>&1; then
    echo "Gerando as chaves..."
    dnssec-keygen -q -a ECDSAP256SHA256 -f KSK -n ZONE "$ZONA" >/dev/null   # KSK: assina as chaves
    dnssec-keygen -q -a ECDSAP256SHA256 -n ZONE "$ZONA" >/dev/null          # ZSK: assina os registros
fi

# -S  usa as chaves da pasta    -N UNIXTIME  serial = data/hora atual
# -e  assinaturas válidas por 1 ano    (sem -3: o CoreDNS só aceita NSEC)
dnssec-signzone -q -S -o "$ZONA" -N UNIXTIME -e +31536000 \
    -f "db.$ZONA.signed" "db.$ZONA" >/dev/null

# A KSK é a chave com flag 257
KSK=$(grep -l "DNSKEY 257" K${ZONA}.+013+*.key)
dnssec-dsfromkey -2 "$KSK" > "$LAB/resolvedor/lab.ds"

chmod 644 "db.$ZONA.signed" "$LAB/resolvedor/lab.ds"

echo "Zona assinada: autoritativo/zonas/db.$ZONA.signed"
echo "Âncora (DS da KSK) em resolvedor/lab.ds:"
cat "$LAB/resolvedor/lab.ds"
