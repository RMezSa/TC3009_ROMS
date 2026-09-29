"""Fase 1: un backend que habla con Ollama.

    tu navegador  ──▶  este Flask  ──▶  Ollama  ──▶  el modelo
      :3000             :8080          :11434      qwen2.5:1.5b
      (fase 2)                         (local)

Un solo endpoint de verdad --POST /api/chat-- y un chequeo de salud.

Este servicio NO guarda la conversacion. Recibe la lista completa de mensajes
en cada peticion, la reenvia, y devuelve la respuesta. Quien recuerda es el
cliente.

    El backend hace UNA cosa y no tiene memoria.
    El estado vive donde se puede ver.

Que sea asi no es pereza: un backend sin estado se puede reiniciar, duplicar y
depurar sin perder nada. Y se nota en la fase 2, cuando el frontend manda la
conversacion entera y ves exactamente que esta recibiendo el modelo.

Hay tres COMPLETA. La guia --docs/practica-ollama.md-- los lleva en orden.
"""

import os

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)

# El frontend vive en el puerto 3000 y esto en el 8080: dos origenes, asi que
# el navegador exige CORS. En la instancia la IP cambia en cada reinicio del
# laboratorio, por eso se autoriza por patron y no por direccion literal.
CORS(app)

# Ollama corre en la MISMA maquina que este backend.
#
# Por eso es localhost, y por eso el puerto 11434 NO se abre en el security
# group: nadie de fuera debe poder preguntarle al modelo directamente saltandose
# tu API. Tu backend es la unica puerta.
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# ─────────────────────────────────────────────────────────────────────────────
#  EL MODELO. Esta es la linea que cambias para usar otro.
# ─────────────────────────────────────────────────────────────────────────────
#
#   1. bajalo:     ollama pull <modelo>
#   2. cambialo:   aqui abajo
#   3. reinicia:   ./run restart
#
# O sin tocar el codigo, para probar uno suelto:
#
#   OLLAMA_MODEL=llama3.2:3b ./run restart
#
# Cabe lo que quepa en 8 GB de RAM y sea razonable en 2 vCPU sin GPU. Mas
# grande no es mejor si tarda un minuto en contestar.
MODELO = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")

# Una t2.large tiene 2 vCPU y NO tiene GPU. Medido en una: unos 6 tokens por
# segundo. Eso convierte dos numeros en decisiones de producto:
#
#   MAX_TOKENS  cuanto puede responder como maximo. Sin tope, una respuesta de
#               400 tokens son mas de un minuto mirando una pantalla quieta.
#   TIMEOUT     cuanto esperamos antes de rendirnos. Sin el, una peticion
#               colgada ocupa un worker para siempre.
MAX_TOKENS = int(os.environ.get("OLLAMA_MAX_TOKENS", "180"))
TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))

# Ollama descarga el modelo de la RAM tras 5 minutos sin usarlo. Eso significa
# que el primer usuario despues de una pausa paga la carga --un giga de disco
# a memoria, en una maquina sin prisa-- y cree que el producto esta roto.
#
# Medido: la primera peticion tardo 5 segundos para 26 tokens; la generacion
# pura era mucho mas rapida. Casi todo era la carga.
#
# 30m lo deja en RAM durante una clase entera. El costo es 1 GB de los 8 que
# tiene la maquina, y es un intercambio que vale la pena: memoria a cambio de
# que nadie espere.
KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "30m")

# Va delante de cada conversacion. Los modelos pequeños se enrollan y se
# inventan cosas; esto los sujeta, y ademas mantiene las respuestas cortas,
# que en una maquina lenta es media experiencia de usuario.
SISTEMA = (
    "Eres un asistente breve y claro. Respondes en español, en dos o tres "
    "frases. Usas solo informacion que aparezca en la conversacion y nunca "
    "inventas datos sobre el usuario."
)


@app.get("/api/health")
def health():
    """Tres preguntas: ¿vivo yo?, ¿vive Ollama?, ¿esta mi modelo?

    Un chequeo que solo diga "ok" no sirve: cuando algo falla, lo que necesitas
    es saber CUAL de las tres cosas, y que hacer.
    """
    # COMPLETA 1 — preguntale a Ollama.
    #
    # GET {OLLAMA}/api/tags devuelve {"models": [{"name": "...", ...}, ...]}.
    #
    # Tres respuestas posibles, y las tres importan:
    #
    #   · Ollama no contesta      -> "degradado", y dile que corra  ollama serve
    #   · contesta pero falta el
    #     modelo de MODELO        -> "degradado", lista los que SI tiene, y
    #                                dile que corra  ollama pull MODELO
    #   · todo bien               -> "ok"
    #
    # Pon un timeout corto (5s): esto es un chequeo de salud, no una pregunta
    # al modelo. Si Ollama esta caido tiene que decirlo rapido.
    try:
        r = requests.get(f"{OLLAMA}/api/tags", timeout=5)
        r.raise_for_status()
        instalados = [m["name"] for m in r.json().get("models", [])]
    except requests.RequestException as e:
        return jsonify({
            "status": "degradado",
            "modelo": MODELO,
            "detalle": f"Ollama no responde en {OLLAMA}: {str(e)[:100]}",
            "arreglo": "En la instancia:  ollama serve",
        })

    if MODELO not in instalados:
        return jsonify({
            "status": "degradado",
            "modelo": MODELO,
            "detalle": f"'{MODELO}' no esta instalado",
            "instalados": instalados,
            "arreglo": f"En la instancia:  ollama pull {MODELO}",
        })

    return jsonify({
        "status": "ok",
        "modelo": MODELO,
        "max_tokens": MAX_TOKENS,
        "keep_alive": KEEP_ALIVE,
    })
    return jsonify({"status": "sin escribir", "modelo": MODELO})


@app.post("/api/chat")
def chat():
    """Recibe la conversacion, devuelve la siguiente respuesta.

    Entra:  {"messages": [{"role": "user", "content": "hola"}, ...]}
    Sale:   {"respuesta": "...", "modelo": "...", "tokens": 42}
    """
    cuerpo = request.get_json(silent=True) or {}
    mensajes = cuerpo.get("messages")

    # Validar ANTES de llamar al modelo. En esta maquina una respuesta cuesta
    # medio minuto de CPU: gastarlo para acabar en un error de formato seria
    # absurdo, y con 30 alumnos a la vez, caro.
    if not isinstance(mensajes, list) or not mensajes:
        return jsonify({"error": 'se esperaba {"messages": [...]} y no llego'}), 400
    for m in mensajes:
        if not isinstance(m, dict) or "role" not in m or "content" not in m:
            return jsonify({
                "error": "cada mensaje necesita 'role' y 'content'",
                "recibido": m,
            }), 400

    # COMPLETA 2 — llama al modelo.
    #
    # POST {OLLAMA}/api/chat con este cuerpo:
    #
    #   {"model": MODELO,
    #    "messages": [...],          <- SISTEMA delante de lo que llego
    #    "stream": False,
    #    "options": {"num_predict": MAX_TOKENS}}
    #
    # Dos detalles que no son adorno:
    #
    #   · el mensaje de SISTEMA lo pone el servidor, no el cliente. Es parte de
    #     como se comporta TU producto, no algo que quien usa el chat deba
    #     poder cambiar desde el navegador.
    #   · num_predict acota la respuesta. Sin tope, una pregunta abierta puede
    #     dar 400 tokens, y a 6 tokens/segundo eso es mas de un minuto.
    #
    # Pasa timeout=TIMEOUT. Sin el, una peticion colgada ocupa un worker para
    # siempre y el siguiente alumno se queda esperando.
    
    try:
        r = requests.post(
            f"{OLLAMA}/api/chat",
            json={
                "model": MODELO,
                # El mensaje de sistema lo pone el servidor, no el cliente: es
                # parte de como se comporta TU producto, y no algo que quien
                # usa el chat deba poder cambiar desde el navegador.
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
        }), 504
    except requests.RequestException:
        return jsonify({
            "error": f"no pude hablar con Ollama en {OLLAMA}",
            "arreglo": "En la instancia:  ollama serve",
        }), 503

    if r.status_code != 200:
        # Ollama dice cosas utiles cuando falla --por ejemplo que el modelo no
        # existe-- y esconderlas tras un 500 generico no ayuda a nadie.
        return jsonify({
            "error": "Ollama rechazo la peticion",
            "detalle": r.text[:200],
        }), 502

    datos = r.json()
    return jsonify({
        "respuesta": datos.get("message", {}).get("content", ""),
        "modelo": MODELO,
        "tokens": datos.get("eval_count", 0),
    })

if __name__ == "__main__":
    print(f"Ollama en {OLLAMA} · modelo {MODELO} · tope {MAX_TOKENS} tokens", flush=True)
    app.run(host="0.0.0.0", port=8080, debug=True)
