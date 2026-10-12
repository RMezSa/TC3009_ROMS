# Fase 3 — Memoria de verdad: PostgreSQL, LangChain y LangGraph

**Una sesión de 4 horas.** Esta guía es autocontenida: no hace falta que las fases
anteriores te hayan quedado perfectas. `fase3/` es una carpeta aparte, con su propio
backend, su propio entorno y su propio script de pruebas.

Hoy vas a hacer tres cosas, y las tres responden a algo que ya viste fallar:

```
   A · La conversación vive en PostgreSQL     porque F5 la borraba
   B · De texto libre a datos con forma       porque el modelo solo devolvía texto
   C · Un grafo que decide, y recuerda        porque tu backend solo sabía hacer una cosa
```

---

## Cómo se reparten las 4 horas

De las cuatro, **3 h 20 min son de trabajo real**: lo demás se va en entrar, instalar y
salir. El plan está hecho para eso, y la parte A es la que importa — si algo se recorta,
se recorta del final.

| | | |
|---|---|---|
| **0:00** | Lanzas la base de datos en AWS | 10 min |
| **0:10** | Mientras se crea: instalas la fase 3 | 20 min |
| **0:30** | **Parte A** — guardar conversaciones en PostgreSQL | 70 min |
| **1:40** | Descanso | 10 min |
| **1:50** | **Parte B** — LangChain: de texto a datos | 30 min |
| **2:20** | **Parte C** — LangGraph: un grafo con memoria, y lo escribes tú | 50 min |
| **3:10** | `bash probar.sh`, y **eliminar la base** | 10 min |
| **3:20** | Fin | |

> **El paso 1 va primero por una razón.** Crear la base tarda de 5 a 15 minutos y no
> depende de ti. Lánzala, y mientras se cocina haces la instalación. Si esperas a
> necesitarla, pierdes ese cuarto de hora mirando una pantalla.

---

## Las dos máquinas

Esto no cambia respecto a lo de siempre, y hoy importa más que nunca porque hay tres
servicios en juego:

```
   TU COMPUTADORA                    TU INSTANCIA                 AWS
   ──────────────                    ────────────                 ───
   VS Code: escribes        ──push──▶  git pull                   RDS
   git add/commit/push                 ./run restart          PostgreSQL
                                       bash probar.sh              ▲
                                       Ollama + el modelo  ────────┘
```

**Tu computadora no ejecuta nada hoy.** Edita y hace `git`. Todo lo que corre, corre en
la instancia — y la base de datos ni siquiera está ahí: está en otra máquina de AWS, al
otro lado de la red. Eso último es medio tema de la sesión.

---

## 0 · Traer la fase 3 a tu repositorio

Como siempre en esta parte: **no hay fork**. Bajas el material y lo subes a un repositorio
tuyo.

**No hace falta nada de las sesiones anteriores.** `fase3/` es independiente: trae su
propio backend, su propio entorno y sus propias dependencias. Si no hiciste las fases 1 y
2, o te quedaron a medias, esta sesión se hace igual.

Mira cuál de los dos casos eres.

### Caso A — ya tienes tu repositorio del curso

**1. Baja el curso.** En
[github.com/vsosahdz/TC3009-Part2-2026](https://github.com/vsosahdz/TC3009-Part2-2026),
botón verde **Code** → **Download ZIP**. Descomprime: te deja `TC3009-Part2-2026-main`.

**2. Copia a tu proyecto una sola carpeta:**

```bash
cp -r ~/Downloads/TC3009-Part2-2026-main/fase3 .
```

> **Solo `fase3/`.** No toques `backend/` ni `frontend/`: son de las fases anteriores, ahí
> está tu código y hoy no se usan.

**3. Súbelo:**

```bash
git status          # debe aparecer solo fase3/
git add -A
git commit -m "fase 3"
git push
```

### Caso B — empiezas de cero

**1. Crea tu repositorio.** En GitHub, **New repository**:

- el nombre que quieras, `TC3009-fase3` está bien
- **Público** — tu instancia lo va a clonar y no tiene credenciales
- **sin** README, sin `.gitignore`, sin licencia

**2. Baja el curso** (igual que el caso A: **Code** → **Download ZIP**, descomprime).

**3. En tu computadora**, crea el proyecto con la carpeta de hoy dentro:

```bash
mkdir TC3009-fase3 && cd TC3009-fase3
cp -r ~/Downloads/TC3009-Part2-2026-main/fase3 .
git init
git add -A
git commit -m "fase 3"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/TC3009-fase3.git
git push -u origin main
```

### Los dos casos, en la instancia

```bash
cd ~
git clone https://github.com/TU-USUARIO/TU-REPO.git   # si aun no lo tienes ahi
cd TU-REPO && git pull
cd fase3
```

A partir de aquí, **todos los comandos de esta guía son dentro de `fase3/`**.

> **¿Sin tiempo para crear el repositorio?** Hoy puedes clonar el del curso directamente
> en la instancia y trabajar ahí:
> `git clone https://github.com/vsosahdz/TC3009-Part2-2026.git && cd TC3009-Part2-2026/fase3`.
> Funciona para la sesión, pero **lo que escribas no queda en ningún repositorio tuyo**:
> al terminar, cópialo a uno antes de apagar la instancia.

---

## 1 · La base de datos (lánzala ya, 10 min)

Vas a crear un PostgreSQL gestionado en **RDS**. No un Postgres dentro de tu instancia, y
el motivo no es comodidad:

```
   EC2 (tu backend)  ──la red──▶  RDS (tus datos)
```

Dos servicios, con su propio endpoint, sus credenciales y su regla de red. Si la base
viviera dentro de la misma máquina aprenderías SQL, pero no aprenderías eso — y «eso» es
lo que separa un servicio de un script. Tu instancia es desechable; tus datos no.

> ### ⚠ Antes de crear nada: la trampa más cara del módulo
>
> **El laboratorio NO detiene las bases de datos al cerrar la sesión**, a diferencia de
> las instancias EC2. Y una base detenida a mano **se vuelve a encender sola a los siete
> días**.
>
> Una RDS olvidada consume tu crédito día y noche aunque no la uses, y se lleva lo que te
> quedaba para el resto del curso.
>
> **Al terminar la sesión la ELIMINAS.** No la detienes: la eliminas. Es el paso 6 de esta
> guía y no es opcional.

### Créala

Consola de AWS → **RDS** → **Create database**:

| Campo | Valor |
| ----- | ----- |
| Creation method | **Standard create** |
| Engine | **PostgreSQL** |
| Templates | **Free tier** |
| DB instance identifier | `chat-db` |
| Master username | `postgres` |
| Master password | **solo letras y números**, y **apúntala** — ver el aviso de abajo |
| Instance class | `db.t3.micro` |
| Storage | 20 GB, **sin** autoscaling |
| **Public access** | **Yes** |
| VPC security group | **Create new**, nómbralo `chat-db-sg` |

**Create database.** Tarda de 5 a 15 minutos — **pasa al paso 2 ahora mismo**.

> ### La contraseña: solo letras y números
>
> La vas a pegar dentro de una URL, y ahí `@`, `/`, `:` y `#` son **separadores**. Una
> contraseña como `Cla/ve@2026` parte la URL por la mitad y el error que sale no se parece
> en nada a la causa:
>
> ```
> failed to resolve host 'postgres'
> ```
>
> Eso parece un problema de red y te manda a mirar el grupo de seguridad durante media
> hora. No lo es: es tu contraseña. Elígela sin símbolos y te ahorras el viaje.
>
> (Si ya la pusiste con símbolos, se pueden escapar —`/` es `%2F`, `@` es `%40`— pero es
> más rápido cambiarla en RDS → **Modify** → **New master password**.)

> **«Public access = Yes» suena mal, y en producción lo es.** Aquí significa «alcanzable
> desde fuera de la VPC»; quién entra de verdad lo decide el grupo de seguridad. En un
> producto real la base no sería pública y la aplicación le hablaría por dentro de la red
> privada.

---

## 2 · Instalar la fase 3 (20 min, mientras la base se crea)

**En la instancia**, dentro de `fase3/`:

```bash
bash setup/instalar.sh
```

Instala y comprueba cuatro capas. Es autocontenido —no da por hecho nada de las fases
anteriores— y si ya tienes Python u Ollama, los detecta y no los reinstala:

```
  1 · paquetes del sistema   python3, venv, psql, curl
  2 · entorno virtual        .venv/ dentro de fase3/
  3 · dependencias           Flask, psycopg, langchain, langgraph  (~60 MB)
  4 · Ollama y el modelo     el servidor y ~1 GB de pesos
```

> `postgresql-client` trae `psql`, que vas a usar para mirar tus tablas. **No** instala un
> servidor de base de datos: el servidor es RDS, que está en otra máquina.

---

## 3 · Conectar las dos cosas (cuando la base esté lista)

### Déjate entrar

Una base recién creada **rechaza todas las conexiones**. Cuando el estado sea
**Available**: entra a la base → **Connectivity & security** → clic en `chat-db-sg` →
**Inbound rules** → **Edit inbound rules** → **Add rule**:

| Type | Source | Para qué |
| ---- | ------ | -------- |
| PostgreSQL (5432) | la IP **privada** de tu EC2, con `/32` | que tu backend hable con ella |

La IP privada está en EC2 → tu instancia → **Private IPv4 address**.

Y **apunta el endpoint**, en la misma pestaña:

```
chat-db.abc123xyz.us-east-1.rds.amazonaws.com
```

### La URL, que no va en el repositorio

**En la instancia:**

```bash
export DATABASE_URL="postgresql://postgres:TU-CLAVE@TU-ENDPOINT.rds.amazonaws.com:5432/postgres"
```

Tu repositorio es público: esa línea **nunca** se escribe en un archivo. Para que no se
pierda al cerrar la terminal, añádela al final de `~/.bashrc` **de la instancia**.

Compruébalo:

```bash
psql "$DATABASE_URL" -c "SELECT version();"
```

> **Se queda colgado y acaba en timeout** → es el grupo de seguridad, no la contraseña.
> Vuelve a la regla de entrada.
>
> **`password authentication failed`** → esa sí es la contraseña. RDS → **Modify** →
> **New master password**.

### El esquema

```bash
psql "$DATABASE_URL" -f setup/esquema.sql
```

```
CREATE TABLE
CREATE TABLE
CREATE INDEX
```

**Comprueba que de verdad están**, que es un minuto ahora o media hora después:

```bash
psql "$DATABASE_URL" -c "\dt"
```

```
              List of relations
 Schema |     Name     | Type  |  Owner
--------+--------------+-------+----------
 public | conversacion | table | postgres
 public | mensaje      | table | postgres
```

> **Si sale `Did not find any relations`**, las tablas se crearon en otra base. Mira lo
> que va después del último `/` en tu `DATABASE_URL`: ese es el nombre de la base, y tiene
> que ser el mismo sitio donde acabas de correr el `CREATE TABLE`.

Ahora ábrelo y léelo, son 20 líneas. Cuatro decisiones que no son de relleno:

**`REFERENCES conversacion(id) ON DELETE CASCADE`** — un mensaje no puede apuntar a una
conversación que no existe, y al borrar una conversación se van sus mensajes. Sin esto
acabas con mensajes huérfanos que nadie sabe de dónde salieron.

**`CHECK (rol IN ('user', 'assistant'))`** — un rol mal escrito se convierte en un chat
que contesta raro y en media hora de depuración. Así el error salta en el `INSERT`, que es
donde está la causa.

**`tokens`** — parece contabilidad y es la columna que convierte «esto cuesta» en una
consulta. Hoy el costo es tiempo; con una API de pago es dinero.

**`TIMESTAMPTZ` y no `TIMESTAMP`** — con zona horaria. Tu instancia está en UTC y tú no.

---

## Parte A · La conversación vive en PostgreSQL (70 min)

Hay **3 `COMPLETA`**: dos en `backend/db.py` y uno en `backend/app.py`.

### Lo que cambia, y es grande

```
   ANTES (fase 1 y 2)                 AHORA
   ──────────────────                 ─────
   {"messages": [...todo...]}         {"mensaje": "hola", "conversacion_id": 7}
   el cliente recuerda                PostgreSQL recuerda
   el payload crecía sin parar        el payload es constante
   F5 borraba la conversación         F5 no borra nada
```

El cliente deja de mandar la conversación entera. Manda **una frase y un número**, y el
historial lo pone la base.

### `COMPLETA 1` — guardar un mensaje

Abre `backend/db.py`. Arriba tienes `crear_conversacion()` **entera, de regalo**: es el
patrón que vas a copiar. Fíjate en dos cosas antes de escribir nada.

```python
    with pool.connection() as con:
        fila = con.execute(
            "INSERT INTO conversacion (titulo, modelo) VALUES (%s, %s) RETURNING id",
            (titulo[:80], modelo),
        ).fetchone()
        return fila[0]
```

**Los valores van en la tupla del final, nunca pegados al texto del SQL.** Esto:

```python
con.execute(f"... WHERE id = {conversacion_id}")     # NO
con.execute("... WHERE id = %s", (conversacion_id,)) # sí
```

La primera forma funciona hasta que alguien escribe una comilla en el chat, y entonces
deja de funcionar — o algo peor. Con `%s` el valor **nunca** se interpreta como SQL: viaja
por un canal distinto. Es la diferencia entre un dato y una instrucción, y es de las pocas
reglas sin excepciones de este curso.

**`RETURNING id`** te ahorra una segunda consulta para preguntar qué número tocó: la base
te lo devuelve en el mismo viaje.

Ahora escribe `guardar_mensaje()`: un `INSERT` en `mensaje` con las cuatro columnas
(`conversacion_id`, `rol`, `contenido`, `tokens`). Este no necesita `RETURNING`.

### `COMPLETA 2` — leer la conversación

Un `SELECT` de `rol` y `contenido`, filtrando por `conversacion_id`, con **`ORDER BY id`**.

Tiene que devolver exactamente esto:

```python
[{"role": "user", "content": "hola"},
 {"role": "assistant", "content": "que tal"}]
```

**Dos trampas, y las dos son silenciosas.**

El `ORDER BY` no es opcional. Sin él PostgreSQL puede devolverte las filas en cualquier
orden, y una conversación desordenada le da al modelo una historia que nunca ocurrió. Hoy
casi siempre saldría bien por suerte; el día que no, el síntoma no se parece a la causa.

Y el idioma: las columnas se llaman `rol` y `contenido` porque son **tuyas**; las claves
tienen que ser `role` y `content` porque son del **API de Ollama**. La traducción ocurre
aquí, en la frontera, y en un solo sitio.

### Para antes de seguir: comprueba `db.py` solo

**No pases al `COMPLETA 3` sin hacer esto.** Son treinta segundos y te ahorran media hora.

Acabas de escribir dos funciones. Si siguieras hasta el final y el chat no recordara,
tendrías que averiguar si falla el `INSERT`, el `SELECT` o el cableado — tres sospechosos
a la vez. Aquí solo hay dos, y ni siquiera hace falta arrancar Flask:

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0, 'backend')
import db
cid = db.crear_conversacion('prueba de db.py', 'qwen2.5:1.5b')
db.guardar_mensaje(cid, 'user', 'hola')
db.guardar_mensaje(cid, 'assistant', 'que tal', 7)
print(db.leer_mensajes(cid))
"
```

Tiene que salir **exactamente** esto:

```python
[{'role': 'user', 'content': 'hola'}, {'role': 'assistant', 'content': 'que tal'}]
```

| Si sale | Qué pasa |
| ------- | -------- |
| `NotImplementedError: COMPLETA 1` | te falta el `INSERT` |
| `NotImplementedError: COMPLETA 2` | te falta el `SELECT` |
| `[]`, una lista vacía | el `SELECT` lee, pero el `INSERT` no guardó |
| `[{'rol': ...` | las claves van en inglés: `role` y `content` |
| `UndefinedColumn` o `UndefinedTable` | el nombre de una columna o de la tabla |

Y míralo desde el otro lado, que es la gracia:

```bash
psql "$DATABASE_URL" -c "SELECT id, rol, contenido, tokens FROM mensaje ORDER BY id;"
```

**Esa es la primera vez que tus datos existen fuera de tu programa.** Puedes apagar el
proceso, apagar la instancia, y siguen ahí.

### `COMPLETA 3` — engancharlo

Abre `backend/app.py`. Cuatro pasos dentro del `try`, y el orden importa:

1. Si `conversacion_id` es `None`, crea una con `db.crear_conversacion(texto, MODELO)`.
   El título es la primera pregunta: basta para reconocerla en una lista.
2. Si **sí** vino un id, comprueba `db.existe(...)`. Si no existe → **404** diciendo cuál.
   Inventar una conversación vacía sería peor: el chat «funcionaría» sin memoria y nadie
   sabría por qué.
3. Lee el historial con `db.leer_mensajes(...)` **antes** de guardar la pregunta nueva.
   Si lo lees después, la pregunta te llega duplicada: una vez de la base y otra de la
   variable `texto`.
4. Guarda la pregunta: `db.guardar_mensaje(id, "user", texto)`.

Deja el historial en una variable llamada `historial`.

> Más abajo, ya escrito, verás que la **respuesta** se guarda después de llamar al modelo.
> Si el modelo falla, la pregunta queda guardada sola. No es un descuido: *pasó de verdad*,
> y un registro que solo guarda lo que salió bien miente justo cuando lo necesitas.

### Pruébalo

**En tu computadora:** `git add -A && git commit -m "parte A" && git push`
**En la instancia:** `git pull && ./run restart`

```bash
./run salud
```

```json
{"base": "ok", "keep_alive": "30m", "max_tokens": 180, "modelo": "qwen2.5:1.5b", "status": "ok"}
```

Tres servicios, tres respuestas. Con tres piezas, «no funciona» deja de servir: lo que
necesitas saber es **cuál**.

```bash
# sin id: empieza una conversacion
curl -s -X POST localhost:8080/api/chat -H 'Content-Type: application/json' \
  -d '{"mensaje":"Me llamo Victor y doy clase de IA. Que es Flask, en una frase?"}'
```

```json
{"conversacion_id": 1, "modelo": "qwen2.5:1.5b", "respuesta": "Flask es...", "tokens": 24}
```

> **Ese número es tuyo y puede no ser 1.** Usa el que te devuelva a ti en el comando
> siguiente. Si copias el mío, le vas a hablar a otra conversación, el modelo contestará
> cosas raras, y **no habrá ningún error que te lo diga**.

```bash
# con TU id, y SOLO una frase
curl -s -X POST localhost:8080/api/chat -H 'Content-Type: application/json' \
  -d '{"conversacion_id":1,"mensaje":"Como me llamo y que doy?"}'
```

**No le mandaste la conversación. La sacó de PostgreSQL.**

### Las tres cosas que hay que ver antes de seguir

**Que la memoria no está en tu backend.**

```bash
./run restart
```

Sigue la misma conversación. Contesta bien. Reiniciaste el proceso, perdiste toda la
memoria de Python, y no pasó nada: la conversación nunca estuvo ahí.

**Que el payload dejó de crecer.** Con la misma conversación, medido:

```
   turno │ fase 2 (lista entera) │ ahora
   ──────┼───────────────────────┼─────────
     1   │       81 bytes        │ 71 bytes
     2   │      259 bytes        │ 64 bytes
     3   │      460 bytes        │ 61 bytes
```

En el turno 20 la versión vieja iría por los 2 000 bytes y subiendo. Con una API de pago
eso se cobra en **cada** petición, y es el motivo real de que los productos acaben
recortando o resumiendo lo viejo.

**Que puedes preguntarle a tus datos.** Esto es lo que no podías hacer cuando la
conversación vivía en un `useState`:

```bash
./run tablas
./run psql
```

```sql
-- ¿Cuánto me ha costado, en tokens?
SELECT sum(tokens) FROM mensaje;

-- ¿Cuál fue la conversación más larga?
SELECT c.id, c.titulo, count(m.id) AS mensajes
  FROM conversacion c JOIN mensaje m ON m.conversacion_id = c.id
 GROUP BY c.id ORDER BY mensajes DESC LIMIT 5;
```

Ninguna de las dos necesitó tocar tu código. **Ese es el cambio de verdad:** los datos
dejaron de ser un detalle de implementación de tu programa.

---

## Parte B · LangChain: de texto libre a datos (30 min)

Aquí no hay nada que rellenar. Es un ejemplo para **correr, leer y tocar**.

```bash
.venv/bin/python ejemplos/langchain_extraccion.py
```

```
  producto       sentimiento  urgente  texto
  ----------------------------------------------------------------------------
  licuadora      negativo     True     Compre la licuadora hace dos dias y ya...
  teclado        positivo     False    El teclado llego bien y escribe comodo...
  La impresora   negativo     False    La impresora imprime rayado desde el m...
  pedido         negativo     False    Me cobraron dos veces el mismo pedido....
  No especifica  positivo     False    Llego todo correcto y antes de la fech...
```

> El tuyo no saldrá idéntico. `producto` es texto libre y `urgente` cambia entre corridas.
> Lo segundo es importante y está explicado abajo.

Cinco frases escritas por personas salieron convertidas en objetos con tres campos. Es lo
**contrario** de lo que hace tu backend: el tuyo devuelve texto para que lo lea un humano;
esto devuelve estructura para que la use un programa.

**Es el puente entre las dos mitades del curso.** En la parte 1 predecías *a partir* de
datos estructurados; aquí los *produces* a partir de texto.

### Lo que te ahorra

Esta línea:

```python
extractor = llm.with_structured_output(Queja)
```

sustituye a: construir el prompt pidiendo JSON, llamar a Ollama, parsear la respuesta,
comprobar que trae los campos, comprobar los tipos, y convertirlo en objeto. Lo escribiste
a mano en la fase 1 — no para este caso, pero sabes cuánto es.

**El precio es que ya no ves lo que pasa dentro.** Ese es el intercambio de todo
framework, y es razonable *una vez que sabes qué hay debajo*. Al revés —aprender el
framework sin haber visto el `requests.post`— lo que aprendes es la librería.

### La lección: el tipo es la instrucción

Abre el archivo y mira:

```python
    sentimiento: Literal["positivo", "negativo", "neutro"]
```

Con `sentimiento: str` y la descripción *"positivo, negativo o neutro"*, este mismo modelo
contesta cosas como `"Insatisfacción"` o `"dissatisfacción y urgencia"`: respeta la
**forma** —es un string— y se inventa el valor. Con `Literal` el valor sale de una lista
cerrada y el problema desaparece.

> **Hazlo tú** (5 min). Cambia `Literal[...]` por `str`, añade
> `= Field(description="positivo, negativo o neutro")`, y vuelve a correrlo. Es la forma
> más rápida de entender por qué un esquema no es documentación.

### Y su límite, que importa más

El esquema garantiza la **forma**, no el **acierto**. Medido, 5 corridas sobre las 5
quejas:

```
  sentimiento   estable en las 5          ← es una categoría cerrada
  urgente       la queja del cobro
                duplicado salió urgente
                4 veces de 5              ← es un juicio
```

Que el dato siempre encaje **no** quiere decir que acierte. Confundir las dos cosas es
como se construyen productos que fallan en silencio: el JSON es perfecto, el programa no
se queja, y la decisión es mala.

Un campo acotado te ahorra validaciones. El acierto hay que **medirlo** — etiquetar a
mano, contar, decidir si alcanza. Exactamente lo que hiciste en la parte 1, y por eso esa
mitad venía primero.

---

## Parte C · LangGraph: un grafo que decide y recuerda (50 min)

```bash
.venv/bin/python ejemplos/langgraph_enrutador.py "Cuanto cuesta la licuadora?"
.venv/bin/python ejemplos/langgraph_enrutador.py "Mi licuadora no enciende, que hago?"
.venv/bin/python ejemplos/langgraph_enrutador.py "A que hora abren los sabados?"
```

Tu backend hace siempre lo mismo: llega una petición, se llama al modelo, se devuelve
texto. Una línea recta. Esto es un camino con bifurcaciones:

```
                        ┌──────────────┐
          START ───────▶│  clasificar  │   el modelo decide la categoría
                        └──────┬───────┘
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
            ┌─────────┐  ┌──────────┐  ┌─────────┐
            │ ventas  │  │ soporte  │  │ general │
            └────┬────┘  └────┬─────┘  └────┬────┘
                 └─────────────┼─────────────┘
                               ▼
                              END
```

Las tres preguntas salen por las tres ramas. **Cada caja es una función normal de
Python**; LangGraph solo pone las flechas y lleva el estado de una a otra.

Fíjate en que `ventas` **ni siquiera llama al modelo**: contesta de un diccionario, que
para un precio es más correcto y además instantáneo. *No todo nodo de un grafo de IA tiene
que usar IA.*

### Por qué este ejemplo y no un agente con herramientas

El ejemplo de LangGraph que sale en todas partes es un agente que decide solo qué
herramientas llamar. **Con el modelo de este curso no funciona**, y está medido:

| | ¿llamó las herramientas? |
| --- | --- |
| `qwen2.5:1.5b` (1.0 GB) | **ninguna**, y respondió en inglés |
| `llama3.2:3b` (2.0 GB) | una de dos, y luego alucinó que «no tenía acceso» |
| `qwen2.5:7b` (4.7 GB) | las dos, correcto |

Haría falta el 7B, que en una t2.large sin GPU va a paso de tortuga. **Clasificar en una
lista cerrada sí lo hace bien** —lo mismo de la parte B— y así la lección es la forma del
grafo, no las ganas del modelo.

Eso también es una decisión de producto: **elegir la arquitectura que tu modelo aguanta**,
no la que sale en los tutoriales.

### El estado vive en tu RDS

Mira la última línea de las tres corridas:

```
  hilo 'demo' lleva atendidas: ['precio']
  hilo 'demo' lleva atendidas: ['precio', 'soporte']
  hilo 'demo' lleva atendidas: ['precio', 'soporte', 'otro']
```

**Son tres procesos de Python distintos.** Cada uno arrancó sin memoria y la lista siguió
creciendo, porque no está en el proceso: está en PostgreSQL. Un cuarto proceso que no
pregunta nada:

```bash
.venv/bin/python ejemplos/langgraph_enrutador.py --estado
```

Para separar conversaciones, cambia el hilo:

```bash
HILO=cliente-7 .venv/bin/python ejemplos/langgraph_enrutador.py "Cuanto cuesta el teclado?"
```

Es el mismo `thread_id` que tu `conversacion_id` de la parte A, con otro nombre.

### Tu turno: añade una cuarta rama (15 min)

Hasta aquí has corrido y leído. Ahora escribe. Abre
`ejemplos/langgraph_enrutador.py` y añade una categoría **`garantia`** con su propio nodo.
Son **cinco** sitios, y recorrerlos es lo que te deja el API del grafo en la cabeza:

1. `class Categoria` → añade `"garantia"` al `Literal`
2. en `clasificar()` → una línea más en el prompt describiendo la categoría
3. una función nueva `def garantia(estado):` que devuelva un `{"respuesta": ...}`
4. `rutear()` → mapea `"garantia"` a `"garantia"`, y añádelo al `Literal` del tipo de vuelta
5. `construir()` → `g.add_node("garantia", garantia)` y mételo en el bucle del `add_edge`

Pruébalo:

```bash
HILO=g4 .venv/bin/python ejemplos/langgraph_enrutador.py "Cuanto dura la garantia?"
HILO=g4 .venv/bin/python ejemplos/langgraph_enrutador.py "Puedo devolver el teclado?"
```

### Lo que vas a encontrar, y es el verdadero ejercicio

**El grafo va a funcionar perfecto. El clasificador no.**

La primera quizá acierte. La segunda casi seguro se va a `otro` o a `soporte`. Medido —
3 corridas sobre 6 preguntas:

```
   las 3 categorías originales .... 9/9    perfectas
   con "garantia" añadida ......... 1/9    casi todo cae en "otro"
```

Y antes de que lo intentes: **reescribir el prompt no lo arregla.** Probé cambiar la
descripción por una lista de palabras clave —`garantia, devolver, devolucion, cambio,
reembolso`— y salió igual de mal. Lo que parecía obvio no funcionó, y esa es media
lección: en esto se mide, no se opina.

**Por qué pasa.** Un modelo de 1.5B distingue bien tres cajones muy distintos entre sí. El
cuarto se solapa: «¿puedo devolver el teclado?» es razonablemente soporte, razonablemente
garantía, y razonablemente ninguna. Al añadir la opción no le diste más capacidad, le
diste más formas de equivocarse.

**Qué harías tú.** No hay una respuesta, hay tres caminos y los tres son reales:

| Camino | Lo que ganas | Lo que pagas |
| ------ | ------------ | ------------ |
| Un modelo más grande | clasifica bien | en una t2.large, segundos por pregunta |
| Quedarte en 3 categorías | funciona siempre | el producto hace menos |
| Filtrar antes del modelo: si el texto trae «garantía», «devolver» o «reembolso», ruta directa | instantáneo y exacto | hay que mantener la lista |

El tercero suele ser el que gana en producto real, y es el que nadie enseña. Tu nodo
`ventas` ya lo hace: contesta de un diccionario sin preguntarle al modelo. **No todo lo
que parece un problema de IA se resuelve con IA.**

### La comparación, que es la clase

```bash
./run tablas
```

```
   checkpoint_blobs       │ del framework
   checkpoint_migrations  │ del framework
   checkpoint_writes      │ del framework
   checkpoints            │ del framework
   conversacion           │ TUYA  (parte A)
   mensaje                │ TUYA  (parte A)
```

`PostgresSaver.setup()` creó sus cuatro tablas solo, y conviven con las tuyas en la misma
base. Ahí está la pregunta de la sesión:

| | Tu versión | La del framework |
| --- | --- | --- |
| Tablas | 2 | 4 |
| Código que escribiste | 3 `COMPLETA` | 1 línea |
| ¿Entiendes el esquema? | entero | habría que estudiarlo |
| «¿cuántos tokens gasté?» | `SELECT sum(tokens)` | el estado está serializado |
| Si necesitas algo raro | lo cambias | esperas, o lo rodeas |

**Ninguna de las dos es la correcta.** Las cuatro tablas son genéricas porque tienen que
servir para cualquier grafo —con ciclos, ramas paralelas, reintentos— y eso se paga en que
ya no puedes preguntarle cosas a tus datos con un `SELECT` simple. Tus dos tablas sirven
para una cosa y la sirven perfecto.

La pregunta útil no es «¿cuál es mejor?» sino **«¿qué estoy construyendo?»**. Y ahora
tienes criterio para decidirlo, porque has hecho las dos.

---

## 5 · Probarlo todo de golpe (5 min)

```bash
bash probar.sh
```

Comprueba las ocho cosas que tienen que funcionar, para cuando falla algo, y dice **qué**
falla y **cómo** arreglarlo. **Tarda unos minutos**: las comprobaciones 5 a 8 hablan con el
modelo de verdad, y en una t2.large eso no es instantáneo.

```
  1. el entorno y las dependencias     5. el chat recuerda (dos turnos)
  2. Ollama y el modelo                6. la memoria está en la BASE
  3. la base de datos y el esquema     7. LangChain: extracción
  4. el backend arranca y da salud     8. LangGraph: enrutado y estado
```

```
  ══════════════════════════════════════════════════════════
    Las 8 comprobaciones pasaron. La fase 3 esta completa.
  ══════════════════════════════════════════════════════════
```

Es seguro correrlo las veces que quieras: **no borra nada**. Lo que sí hace es *añadir*
una conversación de prueba en cada corrida —la verás en `./run tablas`, se llama «Me llamo
Victor y doy clase de IA»— porque para comprobar que el chat recuerda tiene que chatear de
verdad. Si te estorban:

```sql
DELETE FROM conversacion WHERE titulo LIKE 'Me llamo Victor%';
```

Y si te atoras a mitad de la sesión, córrelo — te dice exactamente en qué paso estás.

---

## 6 · Antes de irte: ELIMINA la base

**No es opcional, y no es «detener».**

RDS → tu base → **Actions** → **Delete**. Desmarca *Create final snapshot*, escribe
`delete me`, confirma.

El laboratorio **no** detiene las RDS al expirar la sesión, y una detenida a mano se
enciende sola a los siete días. Tu código está en tu repositorio; la base es desechable.

Y haz el último `push`:

```bash
git add -A && git commit -m "fase 3 completa" && git push
```

---

## Si te atoras

```bash
./run status        # ¿backend? ¿Ollama? ¿base?
./run salud         # las tres, con detalle
./run logs          # el error completo
./run tablas        # qué hay guardado
bash probar.sh      # las 8 comprobaciones
```

| Síntoma | Qué pasa |
| ------- | -------- |
| `"base": "sin configurar"` | Falta `DATABASE_URL` en esa terminal. `export` y `./run restart` |
| `"base": "caida"` | La URL existe pero no contesta: ¿**Available**? ¿la regla de entrada? |
| `psql` se cuelga y da timeout | El grupo de seguridad. Un error de contraseña responde rápido |
| `failed to resolve host 'postgres'` | **No es la red: es tu contraseña.** Tiene un `@`, `/`, `:` o `#` y parte la URL. Cámbiala en RDS → Modify |
| `password authentication failed` | Esa sí es la contraseña. RDS → Modify |
| `relation "conversacion" does not exist` | Creaste las tablas en otra base. Mira lo que va después del último `/` en tu `DATABASE_URL` |
| `COMPLETA 1/2/3` en la respuesta | Ese hueco sigue vacío |
| El chat contesta pero **no recuerda** | `COMPLETA 2`: ¿lleva `ORDER BY id`? ¿devuelve `role` y `content`, no `rol` y `contenido`? |
| Recuerda, pero la base está vacía | `COMPLETA 1`: el `INSERT` no está guardando |
| `ModuleNotFoundError: No module named 'db'` | `db.py` va en `backend/`, al lado de `app.py` |
| `current transaction is aborted` | Una consulta falló antes. `./run restart` lo limpia; la causa está en `./run logs` |
| El nodo de soporte dice tonterías | Es un 1.5B. En una prueba inventó que una licuadora tiene «tapa del agua». El grafo funciona; el modelo no da para más — y distinguir esas dos cosas al depurar es media habilidad |

---

## Lo que cambió, en una línea

```
   Fase 1   el backend no recuerda; recuerda el cliente
   Fase 2   el cliente recuerda en useState; F5 lo borra
   Fase 3   recuerda PostgreSQL; el proceso puede morir y reiniciarse
```

Cada paso movió la memoria a un sitio más duradero, y cada paso costó algo: la fase 2 ganó
una pantalla y pagó un payload que crecía; esta ganó durabilidad y pagó un servicio más que
puede fallar —por eso `/api/health` ahora informa de tres cosas.

**No hay una arquitectura correcta; hay intercambios que se eligen a sabiendas.**
