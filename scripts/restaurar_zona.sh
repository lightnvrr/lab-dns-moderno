#!/usr/bin/env bash
# Desfaz a quebra: reassina a zona a partir do arquivo original.
# Rode dentro do cliente-a:  bash /lab/scripts/restaurar_zona.sh
set -euo pipefail
LAB="${LAB:-/lab}"
bash "$LAB/scripts/assinar_zona.sh" >/dev/null
echo "Zona reassinada. Em uns 15 segundos (recarga da zona + cache da resposta inválida)"
echo "banco.lab.internal volta a responder 10.0.0.43 com a flag ad."
