#!/usr/bin/env bash
# Cria o certificado autoassinado usado pelo DoT e pelo DoH da borda.
# Rode dentro do cliente-a:  bash /lab/scripts/gerar_certificado.sh
set -euo pipefail

LAB="${LAB:-/lab}"
mkdir -p "$LAB/borda/certs"

openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 365 \
    -keyout "$LAB/borda/certs/key.pem" -out "$LAB/borda/certs/cert.pem" \
    -subj "/CN=dns.lab.internal" \
    -addext "subjectAltName=DNS:dns.lab.internal,IP:172.20.0.53,IP:172.21.0.53,IP:172.22.0.53" \
    2>/dev/null

# O CoreDNS precisa conseguir ler a chave. Aceitável só em laboratório.
chmod 644 "$LAB/borda/certs/key.pem" "$LAB/borda/certs/cert.pem"
echo "Certificado criado em borda/certs/"
