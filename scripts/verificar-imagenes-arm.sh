#!/usr/bin/env bash
# T01: verifica que las imágenes previstas publican una variante linux/arm64
# (la arquitectura de las instancias Oracle Always Free). No descarga las imágenes,
# solo consulta su manifiesto. Sale con código 1 si alguna no tiene arm64.
set -uo pipefail

IMAGENES=(
  "pgvector/pgvector:pg16"
  "python:3.12-slim"
  "node:22-slim"
  "grobid/grobid:0.9.1-crf"
)

faltan=0
for imagen in "${IMAGENES[@]}"; do
  if ! manifiesto=$(docker buildx imagetools inspect "$imagen" --format '{{json .Manifest}}' 2>&1); then
    if ! manifiesto=$(docker manifest inspect "$imagen" 2>&1); then
      echo "[NO ENCONTRADA] $imagen"
      faltan=1
      continue
    fi
  fi
  if grep -q '"arm64"' <<<"$manifiesto"; then
    echo "[OK arm64]      $imagen"
  else
    echo "[SIN arm64]     $imagen"
    faltan=1
  fi
done

if [ "$faltan" -ne 0 ]; then
  echo "Alguna imagen no tiene arm64: registrarlo en docs/decisiones/ antes de continuar (T01, R-03)."
fi
exit "$faltan"
