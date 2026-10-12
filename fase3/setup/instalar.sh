#!/usr/bin/env bash
#
# Deja la fase 3 lista en tu INSTANCIA.
#
#   bash setup/instalar.sh
#
# Es autocontenido: no da por hecho que terminaste las fases anteriores. Si ya
# tienes Python u Ollama, los detecta y no los reinstala.
#
#   1. paquetes del sistema   python3, venv, psql, curl
#   2. entorno virtual        .venv/ dentro de fase3/
#   3. dependencias           Flask, psycopg, langchain, langgraph
#   4. Ollama y el modelo     el servidor y ~1 GB de pesos
#
# NO toca tu base de datos: eso lo hace la guia, porque primero tienes que
# crearla en la consola de AWS.

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELO="${OLLAMA_MODEL:-qwen2.5:1.5b}"
VENV="$AQUI/.venv"

VERDE="\033[32m"; ROJO="\033[31m"; AMARILLO="\033[33m"; RESET="\033[0m"
paso()  { echo; echo "==> $1"; }
ok()    { echo -e "    ${VERDE}OK${RESET}  $1"; }
aviso() { echo -e "    ${AMARILLO}!${RESET}   $1"; }
morir() { echo -e "    ${ROJO}FALLA${RESET} $1" >&2; exit 1; }

if [[ "$(uname -s)" != "Linux" ]]; then
  cat <<'FIN' >&2
Este script es para tu INSTANCIA (Ubuntu), no para tu computadora.

Tu maquina edita y hace git; la instancia ejecuta.

  En tu computadora:  git add -A && git commit -m "..." && git push
  En la instancia:    git pull && bash setup/instalar.sh
FIN
  exit 1
fi

# ---------------------------------------------------------------------------
paso "0 · Espacio en disco"
# ---------------------------------------------------------------------------
LIBRE_GB="$(df -BG --output=avail "$AQUI" 2>/dev/null | tail -1 | tr -dc '0-9' || true)"
if [[ -z "$LIBRE_GB" ]]; then
  aviso "no pude medir el disco; sigo"
elif (( LIBRE_GB < 4 )); then
  morir "quedan ${LIBRE_GB} GB y hacen falta al menos 4.
        Amplia el volumen en EC2 > Volumes > Modify volume."
else
  ok "${LIBRE_GB} GB libres"
fi

# ---------------------------------------------------------------------------
paso "1 · Paquetes del sistema"
# ---------------------------------------------------------------------------
# postgresql-client trae psql, que vas a usar para mirar tus tablas. No instala
# un servidor de base de datos: el servidor es RDS, que esta en otra maquina.
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 python3-venv curl ca-certificates lsof postgresql-client
command -v python3 >/dev/null || morir "python3 no quedo instalado"
ok "python $(python3 --version 2>&1 | cut -d' ' -f2) · psql $(psql --version | awk '{print $3}')"

# ---------------------------------------------------------------------------
paso "2 · Entorno virtual"
# ---------------------------------------------------------------------------
# Ubuntu protege el Python del sistema (PEP 668): un 'pip install' fuera de un
# entorno se niega con "externally-managed-environment". Por eso todo vive en
# .venv/, y por eso ./run llama a .venv/bin/python sin pedirte que actives nada.
if [[ -x "$VENV/bin/python" ]]; then
  ok "ya existia en .venv/"
else
  python3 -m venv "$VENV" || morir "no se pudo crear el entorno virtual"
  ok "creado en .venv/"
fi
"$VENV/bin/python" -m pip install -q --upgrade pip
ok "pip $("$VENV/bin/pip" --version | cut -d' ' -f2)"

# ---------------------------------------------------------------------------
paso "3 · Dependencias"
# ---------------------------------------------------------------------------
echo "    instalando (~60 MB, tarda un minuto)"
"$VENV/bin/pip" install -q -r "$AQUI/backend/requirements.txt"
# flask.__version__ esta deprecado y suelta un aviso feo en la pantalla del
# alumno. La version se pregunta a los metadatos del paquete, que es donde vive.
"$VENV/bin/python" - <<'PY' || morir "las dependencias no se pueden importar"
import importlib.metadata as meta

import flask, psycopg, langchain, langgraph  # noqa: F401

print(f"    OK  Flask {meta.version('flask')} · psycopg {meta.version('psycopg')}")
PY
ok "langchain y langgraph importan"

# ---------------------------------------------------------------------------
paso "4 · Ollama"
# ---------------------------------------------------------------------------
if command -v ollama >/dev/null 2>&1; then
  ok "ya estaba instalado"
else
  curl -fsSL https://ollama.com/install.sh | sh
  command -v ollama >/dev/null || morir "la instalacion de Ollama no dejo el comando"
  ok "instalado"
fi

if curl -s --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
  ok "el servidor responde en el 11434"
else
  sudo systemctl enable --now ollama 2>/dev/null || (nohup ollama serve >/dev/null 2>&1 &)
  for _ in $(seq 1 12); do
    sleep 2
    curl -s --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1 && break
  done
  curl -s --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1 \
    || morir "Ollama no respondio. Prueba a mano:  ollama serve"
  ok "servidor arrancado"
fi

if curl -s --max-time 5 http://localhost:11434/api/tags | grep -q "\"$MODELO\""; then
  ok "$MODELO ya estaba descargado"
else
  echo "    bajando $MODELO (~1 GB, tarda unos minutos)"
  ollama pull "$MODELO" || morir "no se pudo descargar $MODELO"
  ok "descargado"
fi

# ---------------------------------------------------------------------------
paso "Comprobacion final"
# ---------------------------------------------------------------------------
fallos=0
[[ -x "$VENV/bin/python" ]] && ok "entorno virtual" || { aviso "falta .venv"; fallos=1; }
"$VENV/bin/python" -c "import flask, psycopg, langgraph" 2>/dev/null \
  && ok "dependencias" || { aviso "faltan dependencias"; fallos=1; }
command -v psql >/dev/null && ok "psql" || { aviso "falta psql"; fallos=1; }
curl -s --max-time 5 http://localhost:11434/api/tags | grep -q "\"$MODELO\"" \
  && ok "$MODELO disponible" || { aviso "falta el modelo"; fallos=1; }

echo
if (( fallos )); then
  echo -e "${ROJO}Algo quedo a medias.${RESET} Vuelve a correr este script."
  exit 1
fi
echo -e "${VERDE}Instancia lista.${RESET} Te falta la base de datos:"
echo
echo "    1. creala en la consola de AWS (la guia, paso 1)"
echo "    2. export DATABASE_URL=\"postgresql://...\""
echo "    3. psql \"\$DATABASE_URL\" -f setup/esquema.sql"
echo "    4. bash probar.sh"
