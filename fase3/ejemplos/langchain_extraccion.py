"""LangChain: de texto libre a datos con forma.

    python ejemplos/langchain_extraccion.py

Tu backend de la fase 1 devuelve texto: una frase que un humano lee. Esto hace
lo contrario -- recibe texto escrito por un humano y devuelve un objeto con
campos, que un programa puede guardar, contar y filtrar.

Es el puente entre las dos mitades del curso: en la parte 1 predecias A PARTIR
de datos estructurados; aqui los PRODUCES a partir de texto.

Lo que hace LangChain por ti, y que tu escribiste a mano en la fase 1:

    construir el prompt, llamar a Ollama, leer el JSON de la respuesta,
    comprobar que trae los campos que esperabas, y convertirlo en un objeto

Una linea --with_structured_output(Queja)-- en vez de cincuenta. El precio de
esa linea es que ya no ves lo que pasa dentro. Por eso lo escribiste primero.
"""

import os

from typing import Literal

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

MODELO = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")


# ─────────────────────────────────────────────────────────────────────────────
#  EL ESQUEMA. Esto es el prompt de verdad.
# ─────────────────────────────────────────────────────────────────────────────
#
# No le estas pidiendo al modelo "devuelveme un JSON y porfa que tenga estos
# campos". Esta clase se traduce a un esquema que Ollama recibe aparte, y la
# respuesta se valida contra el. Si no encaja, revienta aqui -- no treinta
# lineas despues, cuando intentas usar un campo que no existe.
class Queja(BaseModel):
    """Una queja de un cliente, ya ordenada."""

    producto: str = Field(description="de que producto habla, una palabra")

    # OJO A ESTA LINEA. Es la diferencia entre que funcione y que casi
    # funcione.
    #
    # Con 'sentimiento: str' y la descripcion "positivo, negativo o neutro",
    # este mismo modelo contesta cosas como "Insatisfaccion" o "dissatisfaccion
    # y urgencia": respeta la FORMA --es un string-- y se inventa el valor.
    #
    # Con Literal, el valor sale de una lista cerrada. Medido: tres corridas,
    # doce extracciones, siempre uno de los tres.
    #
    #     El tipo no documenta la instruccion. El tipo ES la instruccion.
    #
    # Pruebalo tu: cambia Literal[...] por str y vuelve a correr esto.
    sentimiento: Literal["positivo", "negativo", "neutro"]

    urgente: bool = Field(description="si el cliente pide atencion inmediata")


QUEJAS = [
    "Compre la licuadora hace dos dias y ya no enciende. Necesito respuesta HOY.",
    "El teclado llego bien y escribe comodo, contento con la compra.",
    "La impresora imprime rayado desde el martes, cuando puedan la revisan.",
    "Me cobraron dos veces el mismo pedido. Quiero mi dinero de vuelta ya.",
    "Llego todo correcto y antes de la fecha. Gracias.",
]


def main():
    # ChatOllama habla con el MISMO Ollama de la fase 1, en el mismo puerto.
    # No hay ningun servicio nuevo: solo otra forma de pedirle las cosas.
    llm = ChatOllama(model=MODELO, base_url=OLLAMA, keep_alive="30m")

    # Y aqui esta todo. El objeto que devuelve ya no responde texto: responde
    # objetos Queja.
    extractor = llm.with_structured_output(Queja)

    print(f"\nExtrayendo con {MODELO}\n")
    print(f"  {'producto':<14} {'sentimiento':<12} {'urgente':<8} texto")
    print("  " + "-" * 76)

    for texto in QUEJAS:
        queja = extractor.invoke(f"Extrae los datos de esta queja:\n{texto}")
        print(
            f"  {queja.producto[:13]:<14} {queja.sentimiento:<12}"
            f" {str(queja.urgente):<8} {texto[:38]}..."
        )

    print("""
  Lo que acaba de pasar
  ---------------------
  Cinco frases que escribio una persona salieron convertidas en objetos con
  tres campos. Ahora se pueden contar, ordenar, guardar en la tabla 'mensaje'
  o mandar a quien atienda las urgentes primero.

  Lo que NO acaba de pasar
  ------------------------
  El esquema garantiza la FORMA, no el ACIERTO. Y es una distincion fina:

    · 'sentimiento' nunca sale INVALIDO. No vas a ver "Insatisfaccion" ni
      "muy enfadado": solo existen tres valores y el modelo elige uno. Y
      ademas elige casi siempre el mismo: cinco corridas sobre estas cinco
      quejas dieron el mismo sentimiento las cinco veces.
    · 'urgente' no. Es un juicio, no una categoria, y se nota: la queja del
      cobro duplicado salio urgente 4 veces de 5. La misma frase, el mismo
      modelo, respuesta distinta.

  Que el dato siempre encaje NO quiere decir que siempre acierte, y confundir
  las dos cosas es como se construyen productos que fallan en silencio: el
  JSON es perfecto, el programa no se queja, y la decision es mala.

  Un campo acotado te ahorra escribir validaciones. El acierto hay que
  MEDIRLO -- etiquetas a mano, contar aciertos, decidir si alcanza. Que es
  exactamente lo que hiciste en la parte 1 con el modelo de casas, y por eso
  esa mitad del curso venia primero.
""")


if __name__ == "__main__":
    main()
