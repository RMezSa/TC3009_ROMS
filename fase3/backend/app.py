"""Un chat que recuerda, porque guarda en PostgreSQL.

    curl/navegador  ──▶  este Flask  ──▶  Ollama  ──▶  el modelo
                          :8080           :11434      qwen2.5:1.5b
                            │
                            ▼
                     PostgreSQL en RDS
                        (la memoria)

Es el mismo backend de la fase 1 con UNA diferencia, y es grande: ya no recibe
la conversacion entera del cliente. Recibe una frase y un numero de
conversacion, y el historial lo pone la base.

    Antes:  {"messages": [...toda la conversacion...]}
    Ahora:  {"mensaje": "hola", "conversacion_id": 7}

Hay 1 COMPLETA en este archivo, y 2 en backend/db.py. La guia los lleva.
"""

import os

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

import db

app = Flask(__name__)
CORS(app)

# Ollama corre en la MISMA maquina que este backend. Por eso es localhost, y
# por eso el 11434 no se abre en el security group: tu backend es la unica
# puerta al modelo.
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# ─────────────────────────────────────────────────────────────────────────────
#  EL MODELO. Esta es la linea que cambias para usar otro.
# ─────────────────────────────────────────────────────────────────────────────
#   1. bajalo:     ollama pull <modelo>
#   2. cambialo:   aqui abajo
#   3. reinicia:   ./run restart
MODELO = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")

MAX_TOKENS = int(os.environ.get("OLLAMA_MAX_TOKENS", "180"))
TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))
KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "30m")

SISTEMA = (
    "Eres un asistente breve y claro. Respondes en español, en dos o tres "
    "frases. Usas solo informacion que aparezca en la conversacion y nunca "
    "inventas datos sobre el usuario."
)


@app.get("/api/health")
def health():
    """Tres servicios, tres respuestas: yo, Ollama y la base.

    Con tres piezas, "no funciona" deja de ser util. Lo que necesitas saber es
    CUAL de las tres, y que hacer.
    """
    try:
        r = requests.get(f"{OLLAMA}/api/tags", timeout=5)
        instalados = [m["name"] for m in r.json().get("models", [])]
    except requests.RequestException:
        return jsonify({
            "status": "degradado",
            "detalle": f"Ollama no responde en {OLLAMA}",
            "arreglo": "En la instancia:  ollama serve",
        })

    if MODELO not in instalados:
        return jsonify({
            "status": "degradado",
            "detalle": f"'{MODELO}' no esta instalado",
            "instalados": instalados,
            "arreglo": f"En la instancia:  ollama pull {MODELO}",
        })

    return jsonify({
        "status": "ok",
        "modelo": MODELO,
        "max_tokens": MAX_TOKENS,
        "keep_alive": KEEP_ALIVE,
        "base": "ok" if db.vivo() else ("caida" if db.hay_base() else "sin configurar"),
    })


@app.post("/api/chat")
def chat():
    """Recibe UN mensaje, devuelve la siguiente respuesta.

    Entra:  {"mensaje": "hola", "conversacion_id": 7}   <- el id es opcional
    Sale:   {"conversacion_id": 7, "respuesta": "...", "modelo": "...", "tokens": 42}
    """
    if not db.hay_base():
        return jsonify({
            "error": "este backend necesita una base de datos y no tiene una",
            "arreglo": "Exporta DATABASE_URL y reinicia:  ./run restart",
        }), 503

    cuerpo = request.get_json(silent=True) or {}
    texto = (cuerpo.get("mensaje") or "").strip()
    conversacion_id = cuerpo.get("conversacion_id")

    # Validar ANTES de gastar medio minuto de CPU en el modelo.
    if not texto:
        return jsonify({"error": 'se esperaba {"mensaje": "..."} y no llego'}), 400

    try:
        # COMPLETA 3 — engancha la base con el modelo.
        #
        # Cuatro pasos, y el ORDEN importa:
        #
        #   1. si conversacion_id es None, crea una nueva con
        #      db.crear_conversacion(texto, MODELO) y quedate con el id.
        #      El titulo es la primera pregunta: suficiente para reconocerla.
        #
        #   2. si SI vino un id, comprueba db.existe(id). Si no existe,
        #      devuelve 404 diciendo cual. Inventar una conversacion vacia
        #      seria peor: el chat "funcionaria" sin memoria y nadie sabria
        #      por que.
        #
        #   3. lee el historial con db.leer_mensajes(conversacion_id)
        #      ANTES de guardar la pregunta nueva. Si lo lees despues, la
        #      pregunta te llega duplicada: una vez de la base y otra de la
        #      variable 'texto'.
        #
        #   4. guarda la pregunta con db.guardar_mensaje(id, "user", texto)
        #
        # Deja el historial en una variable llamada 'historial'.
        raise NotImplementedError(
            "COMPLETA 3: falta enganchar la base en backend/app.py"
        )
    except NotImplementedError:
        raise
    except Exception as e:  # noqa: BLE001
        return jsonify({
            "error": "la base de datos no respondio",
            "detalle": str(e)[:200],
            "arreglo": "Comprueba DATABASE_URL y el grupo de seguridad de RDS",
        }), 503

    mensajes = historial + [{"role": "user", "content": texto}]

    try:
        r = requests.post(
            f"{OLLAMA}/api/chat",
            json={
                "model": MODELO,
                # El mensaje de sistema lo pone el servidor, no el cliente.
                "messages": [{"role": "system", "content": SISTEMA}] + mensajes,
                "stream": False,
                "options": {"num_predict": MAX_TOKENS},
                "keep_alive": KEEP_ALIVE,
            },
            timeout=TIMEOUT,
        )
    except requests.Timeout:
        return jsonify({
            "error": f"el modelo tardo mas de {TIMEOUT}s",
            "pista": "normal en una t2.large si la pregunta pide mucho texto",
            "conversacion_id": conversacion_id,
        }), 504
    except requests.RequestException:
        return jsonify({
            "error": f"no pude hablar con Ollama en {OLLAMA}",
            "arreglo": "En la instancia:  ollama serve",
            "conversacion_id": conversacion_id,
        }), 503

    if r.status_code != 200:
        return jsonify({
            "error": "Ollama rechazo la peticion",
            "detalle": r.text[:200],
            "conversacion_id": conversacion_id,
        }), 502

    datos = r.json()
    respuesta = datos.get("message", {}).get("content", "")
    tokens = datos.get("eval_count", 0)

    # La pregunta ya se guardo arriba; aqui va la respuesta. Si el modelo
    # hubiera fallado, la pregunta queda guardada sola -- y eso esta bien:
    # paso de verdad, y un registro que solo guarda lo que salio bien miente
    # justo cuando lo necesitas.
    db.guardar_mensaje(conversacion_id, "assistant", respuesta, tokens)

    return jsonify({
        "conversacion_id": conversacion_id,
        "respuesta": respuesta,
        "modelo": MODELO,
        "tokens": tokens,
    })


@app.get("/api/conversaciones")
def conversaciones():
    """Las ultimas conversaciones. Esto hace visible la persistencia."""
    if not db.hay_base():
        return jsonify({"error": "sin base de datos configurada"}), 503
    try:
        filas = db.listar_conversaciones()
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": "la base no respondio", "detalle": str(e)[:200]}), 503
    for f in filas:
        f["creada_en"] = f["creada_en"].isoformat()
    return jsonify(filas)


@app.get("/api/conversaciones/<int:conversacion_id>")
def conversacion(conversacion_id):
    """Los mensajes de una conversacion."""
    if not db.hay_base():
        return jsonify({"error": "sin base de datos configurada"}), 503
    try:
        if not db.existe(conversacion_id):
            return jsonify({"error": f"no existe la conversacion {conversacion_id}"}), 404
        return jsonify({
            "conversacion_id": conversacion_id,
            "mensajes": db.leer_mensajes(conversacion_id),
        })
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": "la base no respondio", "detalle": str(e)[:200]}), 503


if __name__ == "__main__":
    print(f"Ollama en {OLLAMA} · modelo {MODELO} · base "
          f"{'configurada' if db.hay_base() else 'SIN CONFIGURAR'}", flush=True)
    app.run(host="0.0.0.0", port=8080, debug=True)
