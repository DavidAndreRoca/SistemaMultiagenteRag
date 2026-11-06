#!/usr/bin/env bash
# T01: comprueba que el servidor de desarrollo tiene las herramientas previstas.
# Ejecutar en la instancia Oracle como cada integrante. Sale con 1 si falta alguna.
set -uo pipefail

falta=0
comprobar() {
  local nombre="$1"; shift
  if salida=$("$@" 2>&1 | head -n 1); then
    echo "[OK]    $nombre: $salida"
  else
    echo "[FALTA] $nombre"
    falta=1
  fi
}

echo "Arquitectura: $(uname -m)"
comprobar "Docker" docker --version
comprobar "Docker Compose" docker compose version
comprobar "Git" git --version
comprobar "Python" python3 --version
comprobar "Node.js" node --version
comprobar "npm" npm --version
comprobar "Claude Code" claude --version

python3 - <<'PY' || falta=1
import sys
ok = sys.version_info[:2] >= (3, 12)
print(("[OK]    " if ok else "[FALLA] ") + f"Python >= 3.12 (encontrado {sys.version_info.major}.{sys.version_info.minor})")
sys.exit(0 if ok else 1)
PY

if docker run --rm pgvector/pgvector:pg16 postgres --version >/dev/null 2>&1; then
  echo "[OK]    contenedor PostgreSQL con pgvector arranca"
else
  echo "[FALLA] no se pudo ejecutar pgvector/pgvector:pg16"
  falta=1
fi
exit "$falta"
