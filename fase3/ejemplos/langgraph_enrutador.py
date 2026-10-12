"""LangGraph: un grafo que decide por donde pasar, y se acuerda.

    python ejemplos/langgraph_enrutador.py "Cuanto cuesta la licuadora?"
    python ejemplos/langgraph_enrutador.py "Mi licuadora no enciende"
    python ejemplos/langgraph_enrutador.py --estado

Tu backend de la fase 1 hace siempre lo mismo: llega una peticion, se llama al
modelo, se devuelve el texto. Una linea recta. Esto es lo otro -- un camino con
bifurcaciones, donde lo que pasa depende de lo que llego:

                        ┌──────────────┐
          START ───────▶│  clasificar  │   el modelo decide la categoria
                        └──────┬───────┘
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
            ┌─────────┐  ┌──────────┐  ┌─────────┐
            │ ventas  │  │ soporte  │  │ general │
            └────┬────┘  └────┬─────┘  └────┬────┘
                 └─────────────┼─────────────┘
                               ▼
                              END

Cada caja es una funcion normal de Python. LangGraph solo pone las flechas, y
guarda el estado entre paso y paso.

POR QUE EL MODELO SOLO CLASIFICA
--------------------------------
El ejemplo de LangGraph que vas a encontrar en todas partes es un agente que
llama herramientas solo. Con el modelo de este curso NO funciona: medido,
qwen2.5:1.5b no llamo ni una sola herramienta y encima contesto en ingles; un
3B llamo una de dos y luego alucino. Hace falta un 7B, que en una t2.large sin
GPU va a paso de tortuga.

Clasificar en una lista cerrada SI lo hace bien --eso tambien esta medido-- y
asi la leccion es la forma del grafo, que es lo que vienes a aprender, en vez
de las ganas del modelo.

LA MEMORIA
----------
El checkpointer guarda el estado de cada hilo en TU PostgreSQL. Es lo mismo que
escribiste a mano en docs/guiaBD.md, hecho por el framework. Al final se
comparan las dos versiones, que ahi esta la clase.

Necesita DATABASE_URL, la misma de la guia de la base de datos.
"""

import operator
import os
import sys

from typing import Annotated, Literal, TypedDict

from langchain_ollama import ChatOllama
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

MODELO = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
URL = os.environ.get("DATABASE_URL", "")

llm = ChatOllama(model=MODELO, base_url=OLLAMA, num_predict=120, keep_alive="30m")


# ─────────────────────────────────────────────────────────────────────────────
#  EL ESTADO. Lo que viaja de caja en caja.
# ─────────────────────────────────────────────────────────────────────────────
#
# Cada nodo recibe el estado y devuelve SOLO lo que cambia. LangGraph junta.
#
# 'atendidas' lleva un Annotated con operator.add, y eso cambia la regla para
# ese campo: en vez de reemplazarse, se SUMA. Por eso la lista crece con cada
# pregunta del mismo hilo en vez de quedarse en la ultima.
class Estado(TypedDict):
    pregunta: str
    categoria: str
    respuesta: str
    atendidas: Annotated[list, operator.add]


class Categoria(BaseModel):
    """En que cajon cae la pregunta de un cliente."""

    valor: Literal["precio", "soporte", "otro"]


clasificador = llm.with_structured_output(Categoria)


# ─────────────────────────────────────────────────────────────────────────────
#  LOS NODOS. Funciones normales.
# ─────────────────────────────────────────────────────────────────────────────

def clasificar(estado: Estado):
    c = clasificador.invoke(
        "Clasifica la pregunta de un cliente.\n"
        "  precio  = pregunta cuanto cuesta algo\n"
        "  soporte = algo no funciona o pide ayuda tecnica\n"
        "  otro    = cualquier otra cosa (horarios, ubicacion, saludos)\n\n"
        f"Pregunta: {estado['pregunta']}"
    )
    return {"categoria": c.valor, "atendidas": [c.valor]}


def ventas(estado: Estado):
    # Un nodo NO tiene por que llamar al modelo. Este contesta de un catalogo,
    # que para un precio es mas correcto y ademas instantaneo.
    precios = {"licuadora": "899 pesos", "teclado": "450 pesos", "impresora": "2,300 pesos"}
    for nombre, precio in precios.items():
        if nombre in estado["pregunta"].lower():
            return {"respuesta": f"[ventas] {nombre.capitalize()}: {precio}."}
    return {"respuesta": "[ventas] No encuentro ese producto en el catalogo."}


def soporte(estado: Estado):
    # Mensaje de sistema aparte, no pegado a la pregunta.
    #
    # Con todo junto en un solo string --"Eres soporte. Problema: ..."-- este
    # modelo repite el enunciado en vez de contestarlo. La instruccion y el
    # dato tienen que ir por canales distintos, igual que SISTEMA iba aparte
    # en el backend de la fase 1.
    r = llm.invoke([
        ("system", "Eres soporte tecnico. Respondes en español, en dos frases, "
                   "y empiezas por el primer paso concreto que debe intentar."),
        ("human", estado["pregunta"]),
    ])
    return {"respuesta": "[soporte] " + r.content.strip()}


def general(estado: Estado):
    return {"respuesta": "[general] Te paso con una persona del equipo."}


# La funcion que elige la flecha. Devuelve el NOMBRE del siguiente nodo.
def rutear(estado: Estado) -> Literal["ventas", "soporte", "general"]:
    return {"precio": "ventas", "soporte": "soporte"}.get(estado["categoria"], "general")


def construir():
    g = StateGraph(Estado)
    g.add_node("clasificar", clasificar)
    g.add_node("ventas", ventas)
    g.add_node("soporte", soporte)
    g.add_node("general", general)

    g.add_edge(START, "clasificar")
    # La unica flecha especial: en vez de ir siempre al mismo sitio, pregunta.
    g.add_conditional_edges("clasificar", rutear)
    for nodo in ("ventas", "soporte", "general"):
        g.add_edge(nodo, END)
    return g


def main():
    if not URL:
        print("Falta DATABASE_URL. Es la misma de docs/guiaBD.md:\n")
        print('  export DATABASE_URL="postgresql://postgres:CLAVE@TU-ENDPOINT'
              '.rds.amazonaws.com:5432/postgres"')
        return 1

    hilo = os.environ.get("HILO", "demo")
    solo_estado = "--estado" in sys.argv
    pregunta = " ".join(a for a in sys.argv[1:] if not a.startswith("--"))

    if not solo_estado and not pregunta:
        print(__doc__.split("\n\n")[1])
        return 1

    with PostgresSaver.from_conn_string(URL) as memoria:
        # Crea sus tablas si no estan. Es idempotente: correrlo de nuevo no
        # rompe nada.
        memoria.setup()
        app = construir().compile(checkpointer=memoria)
        config = {"configurable": {"thread_id": hilo}}

        if solo_estado:
            guardado = app.get_state(config).values
            print(f"\n  hilo '{hilo}' — lo que hay guardado en PostgreSQL:\n")
            if not guardado:
                print("    (vacio: todavia no has preguntado nada en este hilo)")
            else:
                print(f"    ultima pregunta : {guardado.get('pregunta')}")
                print(f"    ultima categoria: {guardado.get('categoria')}")
                print(f"    atendidas       : {guardado.get('atendidas')}")
            print()
            return 0

        estado = app.invoke({"pregunta": pregunta, "atendidas": []}, config)

    print(f"\n  pregunta  : {pregunta}")
    print(f"  categoria : {estado['categoria']}   -> nodo '{rutear(estado)}'")
    print(f"  respuesta : {estado['respuesta']}")
    print(f"\n  hilo '{hilo}' lleva atendidas: {estado['atendidas']}")
    print("  (esa lista vive en PostgreSQL, no en este proceso: vuelve a "
          "correrlo y crece)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
