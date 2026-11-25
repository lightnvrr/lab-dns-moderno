#!/usr/bin/env bash
# Preparação de primeira vez: assina a zona e cria o certificado.
# No computador (PowerShell, Git Bash ou terminal):
#   docker compose run --rm cliente-a bash /lab/scripts/preparar.sh
set -euo pipefail
LAB="${LAB:-/lab}"
bash "$LAB/scripts/assinar_zona.sh"
echo
bash "$LAB/scripts/gerar_certificado.sh"
echo
echo "Pronto. Agora rode: docker compose up -d"
