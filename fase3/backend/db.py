"""Todo lo que este producto sabe de PostgreSQL vive aqui.

SQL directo, sin ORM. El resto del backend no ve una sola consulta: si mañana
esto fuera otra base, se cambia este archivo y nada mas.

Hay 2 COMPLETA en este archivo. La guia los lleva en orden.
"""

import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# La direccion y las credenciales NUNCA van en el repositorio.
#
#   export DATABASE_URL="postgresql://postgres:CLAVE@TU-ENDPOINT.rds.amazonaws.com:5432/postgres"
#
# Si falta, el backend arranca igual y lo dice en /api/health. Eso es
# deliberado: una base caida no debe impedirte ver que el resto vive.
URL = os.environ.get("DATABASE_URL", "")

# UN POOL, NO UNA CONEXION POR PETICION.
#
# RDS esta al otro lado de la red: abrir una conexion cuesta entre 50 y 100 ms
# --saludo TCP, autenticacion, arranque de sesion-- y eso se paga en CADA
# peticion si no se reutiliza. El pool las mantiene abiertas y te las presta.
#
# open=False y luego .open(): asi un RDS que todavia esta aprovisionando no
# tumba el arranque del backend.
pool = ConnectionPool(URL, min_size=1, max_size=4, open=False) if URL else None
if pool is not None:
    try:
        pool.open(wait=True, timeout=10)
    except Exception:  # noqa: BLE001
        pass  # /api/health lo dira


def hay_base():
    """¿Esta configurada la base? No dice si responde, solo si existe la URL."""
    return pool is not None


def vivo():
    """¿Contesta de verdad? Esto SI va a la red."""
    if pool is None:
        return False
    try:
        with pool.connection(timeout=5) as con:
            con.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False


def crear_conversacion(titulo, modelo):
    """Empieza una conversacion y devuelve su id.

    Esta te la doy entera, porque es el patron que vas a copiar en el
    COMPLETA 1: fijate en DOS cosas.

      · los valores van en la TUPLA del final, nunca pegados al texto del SQL
      · RETURNING id evita una segunda consulta para preguntar que numero
        toco: la base lo devuelve en el mismo viaje
    """
    with pool.connection() as con:
        fila = con.execute(
            "INSERT INTO conversacion (titulo, modelo) VALUES (%s, %s) RETURNING id",
            (titulo[:80], modelo),
        ).fetchone()
        return fila[0]


def guardar_mensaje(conversacion_id, rol, contenido, tokens=None):
    """Añade un mensaje a una conversacion."""
    # COMPLETA 1 — guarda el mensaje.
    #
    # Un INSERT en 'mensaje' con las cuatro columnas:
    #
    #     conversacion_id, rol, contenido, tokens
    #
    # Copia la forma de crear_conversacion de aqui arriba. Este no necesita
    # RETURNING: no vas a usar el id del mensaje para nada.
    #
    # Los cuatro valores van en la tupla, con %s en el SQL. NUNCA con un
    # f-string: lo que escribe un usuario en el chat no puede acabar siendo
    # interpretado como SQL.
    raise NotImplementedError("COMPLETA 1: falta el INSERT en backend/db.py")


def leer_mensajes(conversacion_id):
    """La conversacion entera, en el formato que espera Ollama.

    Tiene que devolver una lista asi:

        [{"role": "user", "content": "hola"},
         {"role": "assistant", "content": "que tal"}]
    """
    # COMPLETA 2 — lee la conversacion.
    #
    # SELECT de 'rol' y 'contenido' en la tabla mensaje, filtrando por
    # conversacion_id, y ORDER BY id.
    #
    # El ORDER BY no es opcional: sin el, PostgreSQL puede devolverte las
    # filas en cualquier orden, y una conversacion desordenada le da al modelo
    # una historia que nunca ocurrio. Hoy casi siempre saldria bien por suerte;
    # el dia que no, el sintoma no se parece en nada a la causa.
    #
    # Y OJO AL IDIOMA. Las columnas se llaman 'rol' y 'contenido' porque son
    # tuyas; las claves tienen que ser 'role' y 'content' porque son del API de
    # Ollama. La traduccion ocurre aqui, en la frontera, y en un solo sitio.
    raise NotImplementedError("COMPLETA 2: falta el SELECT en backend/db.py")


def listar_conversaciones(limite=20):
    """Las ultimas conversaciones, para poder verlas desde fuera."""
    # row_factory va en el CURSOR, no en la conexion.
    #
    # La conexion es PRESTADA: al salir del with vuelve al pool y se la lleva
    # otro. Si le cambias el row_factory, el siguiente que la use recibe
    # diccionarios donde esperaba tuplas -- y como iterar un diccionario da
    # sus CLAVES, leer_mensajes devolveria {"role": "rol"} y el chat perderia
    # la memoria sin un solo error en los logs.
    #
    # Lo prestado se devuelve como estaba.
    with pool.connection() as con, con.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "SELECT c.id, c.titulo, c.modelo, c.creada_en,"
            "       count(m.id) AS mensajes,"
            "       coalesce(sum(m.tokens), 0) AS tokens"
            "  FROM conversacion c"
            "  LEFT JOIN mensaje m ON m.conversacion_id = c.id"
            " GROUP BY c.id"
            " ORDER BY c.id DESC"
            " LIMIT %s",
            (limite,),
        ).fetchall()


def existe(conversacion_id):
    """¿Existe esa conversacion? Para no inventar historias que no estan."""
    with pool.connection() as con:
        return con.execute(
            "SELECT 1 FROM conversacion WHERE id = %s", (conversacion_id,)
        ).fetchone() is not None
