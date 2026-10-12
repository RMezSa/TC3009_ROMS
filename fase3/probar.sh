#!/usr/bin/env bash
#
# Prueba la fase 3 ENTERA de una sola vez.
#
#   bash probar.sh
#
# Comprueba, en orden, las ocho cosas que tienen que funcionar:
#
#   1. el entorno y las dependencias        5. el chat recuerda (dos turnos)
#   2. Ollama y el modelo                   6. la memoria esta en la BASE
#   3. la base de datos y el esquema        7. LangChain: extraccion
#   4. el backend arranca y da salud        8. LangGraph: enrutado y estado
#
# Para cuando falla algo, y dice QUE falla y COMO arreglarlo. Es seguro
# correrlo las veces que quieras: no borra nada tuyo.

set -uo pipefail
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$AQUI"

VERDE="\033[32m"; ROJO="\033[31m"; AMARILLO="\033[33m"; AZUL="\033[36m"; RESET="\033[0m"
PY="$AQUI/.venv/bin/python"
fallos=0
arrancado_por_mi=0

titulo() { echo; echo -e "${AZUL}$1${RESET}"; echo "────────────────────────────────────────────────────────────"; }
ok()     { echo -e "  ${VERDE}OK${RESET}    $1"; }
mal()    { echo -e "  ${ROJO}FALLA${RESET} $1"; fallos=$((fallos+1)); }
pista()  { echo -e "        ${AMARILLO}→${RESET} $1"; }
fin()    { echo; echo -e "${ROJO}Me detengo aqui.${RESET} Arregla eso y vuelve a correrme."; limpiar; exit 1; }
limpiar() { (( arrancado_por_mi )) && ./run stop >/dev/null 2>&1; return 0; }
trap limpiar EXIT

echo
echo "══════════════════════════════════════════════════════════"
echo "  Fase 3 — prueba completa"
echo "══════════════════════════════════════════════════════════"

# ─── 1 ───────────────────────────────────────────────────────────────────────
titulo "1 · El entorno"
if [[ -x "$PY" ]]; then
  ok "entorno virtual ($("$PY" --version 2>&1 | cut -d' ' -f2))"
else
  mal "no hay entorno en .venv/"; pista "bash setup/instalar.sh"; fin
fi
faltan=$("$PY" - 2>/dev/null <<'PY'
import importlib

mods = {"flask": "Flask", "psycopg": "psycopg", "psycopg_pool": "psycopg_pool",
        "langchain_ollama": "langchain-ollama", "langgraph": "langgraph",
        "langgraph.checkpoint.postgres": "langgraph-checkpoint-postgres"}
falta = []
for modulo, paquete in mods.items():
    try:
        importlib.import_module(modulo)
    except Exception:
        falta.append(paquete)
print(" ".join(falta))
PY
)
if [[ -z "$faltan" ]]; then
  ok "las dependencias importan"
else
  mal "faltan: $faltan"; pista ".venv/bin/pip install -r backend/requirements.txt"; fin
fi

# ─── 2 ───────────────────────────────────────────────────────────────────────
titulo "2 · Ollama y el modelo"
MODELO="${OLLAMA_MODEL:-qwen2.5:1.5b}"
OLLAMA="${OLLAMA_URL:-http://localhost:11434}"
if curl -s --max-time 5 "$OLLAMA/api/tags" >/dev/null 2>&1; then
  ok "Ollama responde en $OLLAMA"
else
  mal "Ollama no responde"; pista "ollama serve"; fin
fi
if curl -s --max-time 5 "$OLLAMA/api/tags" | grep -q "\"$MODELO\""; then
  ok "$MODELO descargado"
else
  mal "no esta $MODELO"; pista "ollama pull $MODELO"; fin
fi

# ─── 3 ───────────────────────────────────────────────────────────────────────
titulo "3 · La base de datos"
if [[ -z "${DATABASE_URL:-}" ]]; then
  mal "DATABASE_URL no esta puesta"
  pista 'export DATABASE_URL="postgresql://postgres:CLAVE@TU-ENDPOINT.rds.amazonaws.com:5432/postgres"'
  fin
fi
ok "DATABASE_URL puesta (${DATABASE_URL##*@})"
if "$PY" -c "
import os, psycopg
psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10).close()" 2>/dev/null; then
  ok "la base responde"
else
  mal "no pude conectar"
  pista "¿Esta 'Available' en la consola? ¿El grupo de seguridad deja entrar a esta maquina?"
  fin
fi
tablas=$("$PY" -c "
import os, psycopg
with psycopg.connect(os.environ['DATABASE_URL']) as c:
    r = c.execute(\"select tablename from pg_tables where schemaname='public'\").fetchall()
    print(' '.join(sorted(t[0] for t in r)))" 2>/dev/null)
if [[ "$tablas" == *conversacion* && "$tablas" == *mensaje* ]]; then
  ok "el esquema esta aplicado (conversacion, mensaje)"
else
  mal "faltan las tablas. Hay: ${tablas:-ninguna}"
  pista "psql \"\$DATABASE_URL\" -f setup/esquema.sql"
  fin
fi

# ─── 4 ───────────────────────────────────────────────────────────────────────
titulo "4 · El backend"
if curl -s -m 3 localhost:8080/api/health >/dev/null 2>&1; then
  ok "ya estaba corriendo"
else
  ./run start >/dev/null 2>&1
  arrancado_por_mi=1
  # Con el recargador de Flask el arranque tarda mas de lo que parece, y en
  # una t2.large mas todavia. Se espera hasta 25s, preguntando.
  for _ in $(seq 1 25); do
    sleep 1
    curl -s -m 3 localhost:8080/api/health >/dev/null 2>&1 && break
  done
  if curl -s -m 5 localhost:8080/api/health >/dev/null 2>&1; then
    ok "arrancado para la prueba"
  else
    mal "no arranca"; pista "./run logs"; fin
  fi
fi
salud=$(curl -s -m 10 localhost:8080/api/health)
estado=$(echo "$salud" | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('status'))" 2>/dev/null)
base=$(echo "$salud" | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('base'))" 2>/dev/null)
[[ "$estado" == "ok" ]] && ok "/api/health dice status=ok" || { mal "/api/health: $salud"; fin; }
[[ "$base" == "ok" ]] && ok "/api/health dice base=ok" || { mal "la base sale como '$base'"; fin; }

# ─── 5 ───────────────────────────────────────────────────────────────────────
titulo "5 · El chat recuerda"
echo "  (dos turnos; en una t2.large esto tarda un poco)"
r1=$(curl -s -m 180 -X POST localhost:8080/api/chat -H 'Content-Type: application/json' \
  -d '{"mensaje":"Me llamo Victor y doy clase de IA. Responde solo Hola."}')
cid=$(echo "$r1" | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('conversacion_id',''))" 2>/dev/null)
if [[ -n "$cid" ]]; then
  ok "primer mensaje -> conversacion $cid"
else
  # Si todavia hay un COMPLETA sin rellenar, Flask devuelve la pagina del
  # depurador --cientos de lineas de HTML-- y volcarla aqui no ayuda a nadie.
  # Se saca solo el renglon que importa.
  hueco=$(echo "$r1" | grep -oE 'COMPLETA [0-9]+[^<"]*' | head -1)
  if [[ -n "$hueco" ]]; then
    mal "$hueco"
    pista "Ese hueco sigue vacio. La guia lo explica; mira tambien ./run logs"
  else
    mal "el primer mensaje fallo: $(echo "$r1" | tr -d '\n' | head -c 160)"
    pista "./run logs"
  fi
  fin
fi
r2=$(curl -s -m 180 -X POST localhost:8080/api/chat -H 'Content-Type: application/json' \
  -d "{\"conversacion_id\":$cid,\"mensaje\":\"Como me llamo?\"}")
texto=$(echo "$r2" | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('respuesta',''))" 2>/dev/null)
# El modelo escribe "Victor" o "Víctor" segun le da, y eso no puede decidir
# si la prueba pasa: un alumno con el codigo bien veria un FALLA inventado.
if echo "$texto" | grep -qiE "v[ií]ctor"; then
  ok "segundo mensaje: recuerda el nombre"
  echo "        \"$(echo "$texto" | head -c 90)\""
else
  mal "no recordo el nombre. Respondio: $(echo "$texto" | head -c 120)"
  pista "Mira el COMPLETA 2: ¿el SELECT lleva ORDER BY id? ¿devuelve 'role' y 'content'?"
fi

# ─── 6 ───────────────────────────────────────────────────────────────────────
titulo "6 · La memoria esta en la base, no en el proceso"
filas=$("$PY" -c "
import os, psycopg
with psycopg.connect(os.environ['DATABASE_URL']) as c:
    n = c.execute('select count(*) from mensaje where conversacion_id=%s', ($cid,)).fetchone()[0]
    print(n)" 2>/dev/null)
if [[ "${filas:-0}" -ge 4 ]]; then
  ok "$filas mensajes guardados en PostgreSQL"
else
  mal "solo hay ${filas:-0} mensajes guardados, esperaba 4"
  pista "Mira el COMPLETA 1: ¿el INSERT guarda de verdad?"
fi
echo "  reinicio el backend y sigo la misma conversacion..."
./run stop >/dev/null 2>&1; ./run start >/dev/null 2>&1; arrancado_por_mi=1
for _ in $(seq 1 25); do
  sleep 1
  curl -s -m 3 localhost:8080/api/health >/dev/null 2>&1 && break
done
r3=$(curl -s -m 180 -X POST localhost:8080/api/chat -H 'Content-Type: application/json' \
  -d "{\"conversacion_id\":$cid,\"mensaje\":\"Repite mi nombre.\"}")
t3=$(echo "$r3" | "$PY" -c "import sys,json; print(json.load(sys.stdin).get('respuesta',''))" 2>/dev/null)
if echo "$t3" | grep -qiE "v[ií]ctor"; then
  ok "proceso NUEVO, memoria cero, y sigue recordando"
  echo "        \"$(echo "$t3" | head -c 90)\""
else
  mal "tras reiniciar no recordo: $(echo "$t3" | head -c 120)"
fi

# ─── 7 ───────────────────────────────────────────────────────────────────────
titulo "7 · LangChain — extraccion estructurada"
if salida=$("$PY" ejemplos/langchain_extraccion.py 2>&1); then
  # Solo las filas de la tabla: sentimiento seguido de True/False. Asi no
  # cuenta de menos cuando el producto sale con dos palabras ("La impresora").
  FILA='\s(positivo|negativo|neutro)\s+(True|False)\s'
  lineas=$(echo "$salida" | grep -cE "$FILA")
  if [[ "$lineas" -eq 5 ]]; then
    ok "las 5 quejas salieron con un sentimiento valido"
    echo "$salida" | grep -E "$FILA" | head -3 | sed 's/^/      /'
  else
    mal "salieron $lineas filas validas de 5"
    pista "Corre a mano:  .venv/bin/python ejemplos/langchain_extraccion.py"
  fi
else
  mal "el ejemplo de LangChain reviento"
  echo "$salida" | tail -3 | sed 's/^/        /'
fi

# ─── 8 ───────────────────────────────────────────────────────────────────────
titulo "8 · LangGraph — enrutado y estado en la base"
HILO="probar-$$"
declare -a esperado=(precio soporte otro)
i=0
for q in "Cuanto cuesta la licuadora?" "Mi licuadora no enciende, que hago?" "A que hora abren los sabados?"; do
  out=$(HILO="$HILO" "$PY" ejemplos/langgraph_enrutador.py "$q" 2>&1)
  cat=$(echo "$out" | grep -oE 'categoria : [a-z]+' | awk '{print $3}')
  if [[ "$cat" == "${esperado[$i]}" ]]; then
    ok "\"${q:0:34}\" -> $cat"
  else
    mal "\"${q:0:34}\" -> ${cat:-nada} (esperaba ${esperado[$i]})"
    echo "$out" | tail -2 | sed 's/^/        /'
  fi
  i=$((i+1))
done
estado_final=$(HILO="$HILO" "$PY" ejemplos/langgraph_enrutador.py --estado 2>&1 | grep -oE "\['.*'\]")
if [[ "$estado_final" == *precio*soporte*otro* ]]; then
  ok "un proceso nuevo lee el estado de PostgreSQL: $estado_final"
else
  mal "el estado no se guardo bien: ${estado_final:-vacio}"
fi

# ─── Resumen ─────────────────────────────────────────────────────────────────
echo
echo "══════════════════════════════════════════════════════════"
if (( fallos )); then
  echo -e "  ${ROJO}$fallos comprobacion(es) fallaron.${RESET}"
  echo "  Cada una de arriba dice que mirar."
else
  echo -e "  ${VERDE}Las 8 comprobaciones pasaron.${RESET} La fase 3 esta completa."
  echo
  echo "  Mira lo que construiste:"
  echo "      ./run tablas"
  echo "      ./run psql"
fi
echo "══════════════════════════════════════════════════════════"
echo
exit $(( fallos > 0 ))
