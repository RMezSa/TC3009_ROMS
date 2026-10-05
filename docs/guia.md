# Práctica — Un producto con un modelo de lenguaje propio

Hasta ahora tu modelo lo entrenaste tú. Este viene hecho, pesa 1 GB, y corre **en tu
instancia**: nada sale a internet, no hay API key, no hay factura por token.

Lo que cambia es todo lo demás. Un modelo de lenguaje no devuelve un número: devuelve texto,
tarda, y a veces se equivoca con total seguridad. Construir un producto encima de eso es un
problema distinto, y esta práctica va de eso.

```
   Fase 1   un backend en Flask que habla con Ollama          ~60 min
   Fase 2a  un frontend en React que habla con el backend     ~45 min
   Fase 2b  la respuesta aparece escribiéndose, no de golpe   ~30 min
```

---

## Dónde se hace cada cosa

El mismo reparto de siempre, con un invitado nuevo:

```
   Tu computadora  ─push──▶  TU repo  ─clone/pull──▶  Tu instancia (t2.large)
   ────────────────                                   ──────────────────────
   VS Code                                            Flask      :8080
   editas, no ejecutas                                React      :3000
                                                      Ollama     :11434  ← local, no se expone
```

**Ollama vive solo en la instancia.** Tu computadora no lo necesita: solo edita código.

Los puertos 8080 y 3000 ya están abiertos en tu security group desde la parte 1, así que no
hay que tocar la consola de AWS. El **11434 no se abre**, y eso es una decisión, no un olvido:
si estuviera abierto, cualquiera podría preguntarle al modelo directamente saltándose tu API —
sin tu validación, sin tu tope de tokens, sin tu registro.

> Tu backend es la única puerta al modelo. Esa frase vale para Ollama y vale igual para
> OpenAI: el día que uses una API de pago, el backend es lo que impide que tu clave viva en el
> navegador de un desconocido.

---

## El modelo

Lo instaló `setup/bootstrap.sh` cuando aprovisionaste la instancia. Compruébalo con
`ollama list`. Lo que sigue es **por qué ese y no otro**, que es la primera decisión de
producto de esta práctica.

### Por qué ese modelo y no otro

Una t2.large tiene 8 GB de RAM, 2 vCPU y **no tiene GPU**. Eso descarta casi todo. Probé los
que sí caben, con la misma pregunta en los tres:

| modelo | tamaño | ¿recuerda la conversación? |
|---|---:|---|
| `llama3.2:1b` | 1.3 GB | **1 de 5** — y además inventa |
| `qwen2.5:1.5b` | 1.0 GB | 5 de 5 |
| `llama3.2:3b` | 2.0 GB | 5 de 5, pero el doble de lento |

El fallo del `1b` no es que olvide, es que **rellena**. Le dije «me llamo Victor, mi color
favorito es el verde» y al preguntarle después respondió, en tres intentos seguidos:

```
· Me llamo Luis y mi color favorito es el rojo.
· Tienes 30 años.
· Te llamo Mateo y mi color favorito es el azul.
```

Un modelo que inventa con esa naturalidad es inservible para conversar, y es la primera cosa
que esta práctica te enseña: **el tamaño del modelo es una decisión de producto**, y la mides
probándola, no leyendo la ficha técnica.

### Lo lento que va, medido

En una t2.large real, con este mismo backend:

```
   26 tokens en 5 segundos   =   4.8 tokens/segundo de extremo a extremo
```

«De extremo a extremo» importa, porque ese número **no es la velocidad del modelo**: incluye
cargar el modelo del disco a la RAM, procesar tu pregunta, generar, y la ida y vuelta por
Flask. Y la primera parte se come casi todo.

### La carga en frío, que es medio problema de producto

Ollama descarga el modelo de la memoria tras **cinco minutos** sin usarlo. La siguiente
pregunta paga la recarga: un gigabyte de disco a RAM, en una máquina sin prisa.

Compruébalo. Pregunta algo, mira lo que tarda, espera, y vuelve a preguntar:

```bash
curl -s http://localhost:11434/api/chat \
  -d '{"model":"qwen2.5:1.5b","stream":false,
       "messages":[{"role":"user","content":"hola"}]}' \
  | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(f\"carga {d.get('load_duration',0)/1e9:.2f}s · generar {d.get('eval_duration',0)/1e9:.2f}s\")"
```

La primera vez la carga domina; la segunda es casi cero. **Ese es el efecto que hace que un
usuario crea que tu producto está roto justo cuando vuelve a usarlo después de un rato.**

Por eso el backend manda `keep_alive`: le pide a Ollama que lo deje en memoria media hora.
Cuesta 1 GB de los 8 que tiene la máquina, y es un intercambio deliberado — memoria a cambio
de que nadie espere.

### Si quieres comparar modelos, hazlo justo

Mi recomendación de `qwen2.5:1.5b` sale de que **no inventa** en conversación, no de que sea
más rápido: en la t2.large eso no lo he medido de forma comparable. Si quieres decidirlo con
tus propios datos, esto mide los dos igual, en caliente y solo la generación:

```bash
for m in qwen2.5:1.5b llama3.2:3b; do
  curl -s http://localhost:11434/api/chat -d "{\"model\":\"$m\",\"stream\":false,
    \"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}" >/dev/null
  curl -s http://localhost:11434/api/chat -d "{\"model\":\"$m\",\"stream\":false,
    \"messages\":[{\"role\":\"user\",\"content\":\"Explica que es una API en tres frases.\"}]}" \
  | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(f\"  $m  {d['eval_count']/(d['eval_duration']/1e9):.1f} tok/s\")"
done
```

La primera llamada calienta el modelo; la segunda es la que cuenta. Sin eso estarías
comparando tiempos de carga, no de generación — que es el error que yo cometí.

---

### Cambiar de modelo: una línea

El modelo por defecto es **`qwen2.5:1.5b`**, y vive en una sola línea de
[backend/app.py](../backend/app.py):

```python
MODELO = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
#                                        ^^^^^^^^^^^^
#                                        esto es lo que cambias
```

Tres pasos, **en la instancia**:

```bash
ollama pull llama3.2:3b     # 1. bájalo
# 2. cambia la línea en backend/app.py (desde tu computadora, y push)
./run restart               # 3. reinicia
./run salud                 # 4. comprueba que dice el nuevo
```

Y para probar uno suelto **sin tocar código**, porque la línea lee una variable de entorno:

```bash
OLLAMA_MODEL=llama3.2:3b ./run restart
```

Eso dura hasta el siguiente `restart` sin la variable. Útil para comparar dos en cinco
minutos sin ensuciar tu repositorio.

### Cuáles caben

La regla no es «el más nuevo»: es **lo que quepa en 8 GB de RAM y sea razonable en 2 vCPU sin
GPU**. Tamaños medidos:

| modelo | tamaño | en una t2.large |
|---|---:|---|
| `qwen2.5:0.5b` | ~0.4 GB | muy rápido, calidad justa |
| **`qwen2.5:1.5b`** | **1.0 GB** | **el que viene por defecto** |
| `llama3.2:1b` | 1.3 GB | rápido, pero **inventa** en conversación |
| `llama3.2:3b` | 2.0 GB | mejor calidad, más lento |
| `phi3` (3.8B) | 2.2 GB | parecido al anterior |
| `qwen2.5:7b` | 4.7 GB | cabe a duras penas, e irá muy lento |

> **`llama3.1` no tiene versión pequeña.** Solo existe en 8B, 70B y 405B: la menor son 4.7 GB
> y en 2 vCPU sin GPU es inusable. Si querías «subir» de `llama3.2` a `llama3.1`, ese salto no
> va en la dirección que parece — el 3.2 es más nuevo para tamaños chicos, no más viejo.
>
> Compruébalo tú antes de bajar nada: en [ollama.com/library](https://ollama.com/library) cada
> modelo lista sus tamaños.

Después de cambiar, **vuelve a hacer las dos pruebas del cierre de esta fase**: que responda, y
que recuerde el dato del turno anterior. Un modelo que pasa la primera y falla la segunda no
sirve para un chat, por rápido que sea — y es exactamente lo que le pasa al `llama3.2:1b`.

---

## Fase 1 — El backend (60 min)

### Antes de escribir nada

Ya tienes tu repositorio y tu instancia aprovisionada — si no,
[00-setup.md](00-setup.md), son quince minutos.

**En la instancia:**

```bash
cd ~/TU-REPO
./run start
./run salud
```

Te va a responder:

```json
{"modelo": "qwen2.5:1.5b", "status": "sin escribir"}
```

Eso es correcto: el esqueleto está vacío. Hay **tres `COMPLETA`** en
[backend/app.py](../backend/app.py), y la aplicación te dice cuál falta conforme avanzas.

### El ciclo, cada vez que escribas algo

```bash
# en tu computadora
git add -A && git commit -m "completa 1" && git push

# en la instancia
git pull && ./run restart && ./run salud
```

### El mapa, antes de escribir

```
   POST /api/chat          ──▶  POST {OLLAMA}/api/chat
   {"messages": [...]}          {"model", "messages", "stream", "options"}
        ▲                                    │
        │                                    ▼
   {"respuesta", "tokens"}  ◀──  {"message": {"content"}, "eval_count"}
```

Tu backend es un **traductor con opiniones**: recibe en tu formato, habla con Ollama en el
suyo, y devuelve en el tuyo. Las opiniones son el mensaje de sistema, el tope de tokens y el
timeout — y son lo que lo convierte en un producto en vez de un proxy.

Y fíjate en lo que **no** hace: guardar la conversación. Recibe la lista completa de mensajes
en cada petición. Quien recuerda es el cliente.

> Un backend sin estado se reinicia, se duplica y se depura sin perder nada. Además, en la
> fase 2 vas a ver exactamente lo que recibe el modelo, porque lo mandas tú.

### `COMPLETA 1` — ¿vive Ollama?

Lo primero no es hablar con el modelo: es saber si está. Reemplaza el `COMPLETA 1` por esto:

```python
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
```

Tres respuestas distintas, y cada una **dice qué hacer**. Un chequeo de salud que solo
responda `ok` o `error` no sirve: cuando algo falla, lo que necesitas es saber cuál de las
tres cosas está mal.

El `timeout=5` es corto a propósito. Esto es un chequeo, no una pregunta al modelo: si Ollama
está caído tiene que decirlo rápido, no colgarse dos minutos.

Guarda, empuja, y en la instancia:

```bash
git pull && ./run restart && ./run salud
```

```json
{"status": "ok", "modelo": "qwen2.5:1.5b", "max_tokens": 180}
```

**Pruébalo roto también**, que es donde se ve si sirve: para Ollama (`pkill ollama`) y vuelve
a pedir salud. Tiene que decirte `ollama serve`. Luego arráncalo otra vez.

### `COMPLETA 2` — la llamada al modelo

```python
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
```

Tres decisiones en ese bloque, y ninguna es de estilo:

**El mensaje de sistema lo pone el servidor.** Va delante de todo y el cliente no puede
tocarlo. Si lo mandara el navegador, cualquiera podría reescribir el comportamiento de tu
producto abriendo las herramientas de desarrollador.

**`num_predict` acota la respuesta.** Sin tope, una pregunta abierta da 400 tokens, y a 6
tokens/segundo eso es **más de un minuto** mirando una pantalla quieta. Lo medí:

```
   sin límite         390 tokens  →  67 s
   num_predict=180    180 tokens  →  31 s
```

No es censura: es que un producto que tarda un minuto en contestar no lo usa nadie. El número
correcto sale de tu medición, no de esta guía.

**`timeout=TIMEOUT`.** Sin él, una petición colgada ocupa un worker para siempre y el
siguiente que pregunte se queda esperando. Con 30 personas contra la misma t2.large, eso pasa.

### `COMPLETA 3` — cuando algo sale mal

```python
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
```

Tres fallos, tres códigos distintos, y cada uno dice qué hacer:

| | | |
|---|---|---|
| `504` | tardó demasiado | es culpa de la máquina, no tuya |
| `503` | Ollama no contesta | `ollama serve` |
| `502` | Ollama rechazó | se reenvía **su** mensaje, que suele nombrar el problema |

Devolver `tokens` parece de adorno y no lo es: es lo que te deja ver el costo de cada
respuesta. Hoy el costo es tiempo; el día que uses una API de pago, es dinero.

### Pruébalo

**En la instancia:**

```bash
curl -s -X POST http://localhost:8080/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Que es una API REST, en dos frases?"}]}'
```

```json
{
  "respuesta": "Una API REST es una herramienta que permite a un programa conectarse a un servicio web...",
  "modelo": "qwen2.5:1.5b",
  "tokens": 41
}
```

### Lo que hay que ver antes de cerrar la fase

**Que no tiene memoria.** Manda dos peticiones por separado:

```bash
curl -s -X POST http://localhost:8080/api/chat -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Me llamo Victor."}]}'

curl -s -X POST http://localhost:8080/api/chat -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Como me llamo?"}]}'
```

No se acuerda, y **está bien**. Ahora manda la conversación entera:

```bash
curl -s -X POST http://localhost:8080/api/chat -H 'Content-Type: application/json' -d '{
  "messages":[
    {"role":"user","content":"Me llamo Victor y doy clase de IA."},
    {"role":"assistant","content":"Hola Victor."},
    {"role":"user","content":"Como me llamo y que doy?"}
  ]}'
```

```
Tu nombre es Victor, y eres un experto en Inteligencia Artificial.
```

**La memoria no está en el modelo ni en tu servidor: está en la lista que mandas.** Eso es
todo lo que hay detrás de que un chat «recuerde», y es exactamente lo que vas a construir en
la fase 2 — porque el frontend va a ser quien guarde esa lista.

**Y que la validación llega antes que el modelo:**

```bash
curl -s -X POST http://localhost:8080/api/chat -H 'Content-Type: application/json' -d '{}'
```

```json
{"error": "se esperaba {\"messages\": [...]} y no llego"}
```

Instantáneo, sin gastar treinta segundos de CPU para acabar en un error de formato. Con 30
personas contra la misma máquina, eso importa.

---

## Fase 2 — El frontend (60 min)

Tu backend funciona y solo lo has usado con `curl`. Eso está bien para probar y es
inservible para enseñárselo a alguien. Ahora la parte que se ve.

Son **dos** `COMPLETA` y ningún archivo que escribas de cero: el esqueleto está en
`frontend/`.

### Primero, trae el material de la fase 2

Cuando clonaste el curso, `frontend/` todavía no existía. Hay que traerlo.

**Baja el ZIP y copia la carpeta.** En
[github.com/vsosahdz/TC3009-Part2-2026](https://github.com/vsosahdz/TC3009-Part2-2026),
botón verde **Code** → **Download ZIP**. Descomprime: te deja una carpeta
`TC3009-Part2-2026-main`. Copia a tu proyecto estas cuatro cosas —arrastrándolas en el
explorador de archivos, o desde la terminal estando en tu proyecto:

```bash
cp -r ~/Downloads/TC3009-Part2-2026-main/frontend .
cp -r ~/Downloads/TC3009-Part2-2026-main/docs .
cp -r ~/Downloads/TC3009-Part2-2026-main/setup .
cp    ~/Downloads/TC3009-Part2-2026-main/run .
```

> **`backend/` NO se copia.** Ahí están tus `COMPLETA` de la fase 1. Copiarla encima te
> devolvería el esqueleto vacío y perderías el trabajo. Es el único error grave de este
> paso.

Comprueba que no te llevaste tu backend por delante, y súbelo:

```bash
git status                 # 'backend/app.py' NO debe aparecer en la lista
git add -A
git commit -m "material de la fase 2"
git push
```

Si `backend/app.py` sí aparece, copiaste de más: `git checkout -- backend/app.py` y repite
el `git add`.

Y en la instancia, donde ahora hace falta Node:

```bash
git pull
bash setup/bootstrap.sh    # ya está casi todo; ahora añade Node y el frontend
./run restart
```

> **¿Prefieres hacerlo con git?** Si tienes el remoto `curso`, son dos comandos:
> `git fetch curso && git merge curso/main --no-edit`. Está explicado, con el caso del ZIP
> y qué hacer si se queja, en [00-setup.md → Traer material nuevo del
> curso](00-setup.md#traer-material-nuevo-del-curso).

### Qué se instaló, y por qué eso

El `bootstrap.sh` ya te dejó Node y las dependencias. Vale la pena saber qué eligió y
por qué, porque las dos decisiones se repiten en cualquier proyecto que hagas después.

**Node 24, y no la más nueva.** Node saca versión cada seis meses. Ahora mismo:

```
  v26   la más nueva. Será LTS en octubre de 2026 — todavía no lo es
  v24   LTS ACTIVA          ← la que se instaló
  v22   en mantenimiento: solo parches de seguridad
  v20   fin de vida
```

«La más nueva» suena a mejor y en herramientas de build suele significar «la que
todavía no tiene arreglado lo que te va a pasar». La LTS activa lleva meses recibiendo
correcciones y es contra la que prueban Vite, TypeScript y todo lo demás. Una versión
por detrás de la punta, a propósito.

**Vite + React + TypeScript, y no Next.js.** Next.js trae enrutado, renderizado en el
servidor y sus propias API routes. Aquí no se usa ninguna de las tres —tu API ya existe,
es el Flask de la fase 1— y cada una es una capa que tendrías que entender para depurar
un fallo. Vite hace una cosa: sirve tu código y lo recarga al guardar.

**TypeScript** hace un trabajo concreto en este proyecto: el tipo `Mensaje` es el
contrato de tu backend escrito de forma que la máquina lo revise. Si mandas un `role`
que no existe, el error aparece mientras escribes, no cuando el modelo devuelve algo
raro y tardas veinte minutos en saber por qué.

### Antes de escribir nada

**En la instancia:**

```bash
./run restart
./run status
```

Tienen que aparecer los dos, `api` y `web`. Abre `http://TU-IP:3000` y vas a ver la
página ya montada: la cabecera dice qué modelo hay, el campo de texto funciona. Escribe
algo y dale a Enviar:

```
No se pudo responder.
COMPLETA 4: falta enviar el mensaje. Esta en src/App.tsx.
```

**Eso es lo correcto.** El esqueleto compila y corre; lo que falta lo dice él mismo, en
la pantalla, con el archivo y todo. No vas a tener que adivinar dónde estabas.

Y los dos huecos están **encadenados**: en cuanto llenes el `COMPLETA 4`, el mismo botón
te va a mandar al `COMPLETA 5`, y cuando llenes ese, contesta el modelo. Si en algún
momento te pierdes, manda un mensaje y lee lo que sale: la aplicación te dice en qué paso
estás.

La cabecera distingue **tres** estados, y conviene saber leerla porque ahorra buscar
donde no es:

| Dice | Qué pasa | Dónde mirar |
| ---- | -------- | ----------- |
| `modelo qwen2.5:1.5b` | todo bien | — |
| `el backend vive, pero Ollama no contesta` | el 8080 contesta, el 11434 no | `ollama serve` |
| `el backend no responde` | el 8080 no contesta | `./run status`, `./run logs api` |

### `COMPLETA 4` — dónde vive la conversación

Abre `src/App.tsx`. Arriba del componente están las cinco piezas de estado, ya escritas:

```tsx
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [texto, setTexto] = useState("");
  const [esperando, setEsperando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [estado, setEstado] = useState<Salud | null>(null);
```

`mensajes` es **la memoria del chat**. No está en el modelo, que no recuerda nada entre
peticiones, ni en tu servidor, que decidiste que no guardara nada. Está en esta línea,
en el navegador de quien lo usa.

Lo que falta es la función que la mueve:

```tsx
  async function mandar(e: FormEvent) {
    e.preventDefault(); // sin esto el navegador recarga la pagina entera
    const pregunta = texto.trim();
    if (!pregunta || esperando) return; // sin envios duplicados

    // La pregunta aparece YA, antes de que el modelo conteste. En una maquina
    // que tarda medio minuto, ver tu propio mensaje es la diferencia entre
    // "esta pensando" y "se rompio".
    const conPregunta: Mensaje[] = [...mensajes, { role: "user", content: pregunta }];
    setMensajes(conPregunta);
    setTexto("");
    setError(null);
    setEsperando(true);

    try {
      const r = await enviar(conPregunta);
      setMensajes([...conPregunta, { role: "assistant", content: r.respuesta }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setEsperando(false);
    }
  }
```

Cuatro decisiones, y ninguna es de estilo.

**`conPregunta` es una variable, no `mensajes` otra vez.** `setMensajes` no cambia
`mensajes` al instante: React vuelve a dibujar y en la pasada *siguiente* la variable
vale otra cosa. Si en el `try` escribieras `[...mensajes, respuesta]`, estarías usando
la lista de antes —sin la pregunta— y la perderías. Este es el error más común de React
y no da ningún aviso: simplemente desaparecen mensajes.

**Pintar antes de llamar.** El `setMensajes(conPregunta)` va *antes* del `await`. A seis
tokens por segundo, media respuesta es medio minuto; una pantalla que no se mueve en ese
rato no parece lenta, parece rota.

**`finally`.** Si `enviar()` lanza y `setEsperando(false)` estuviera solo en el camino
bueno, el botón se quedaría deshabilitado para siempre y habría que recargar la página.
Un error recuperable convertido en uno fatal, por dónde pusiste una línea.

**El error se guarda, no se esconde.** `err.message` es el texto que escribiste en la
fase 1 —`ollama serve`, `ollama pull ...`— y llega hasta la pantalla sin que nadie lo
traduzca. Todo ese trabajo del backend valía para esto.

Guarda y manda un mensaje. **Todavía no contesta el modelo**, y la pantalla te dice por
qué:

```
No se pudo responder.
COMPLETA 5: falta la llamada a http://TU-IP:8080/api/chat, en src/api.ts (iba a mandar 1 mensaje(s))
```

Ese es el `enviar()` que acabas de llamar y que aún está vacío. Tu `try/catch` funciona
—atrapó el error y lo pintó— y te acaba de señalar el siguiente hueco.

### `COMPLETA 5` — la costura

Todo lo que el frontend sabe del servidor cabe en una función. Abre `src/api.ts`:

```ts
export async function enviar(messages: Mensaje[]): Promise<Respuesta> {
  const r = await fetch(`${API}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });

  const datos = await r.json().catch(() => ({}));

  if (!r.ok) {
    // El backend dice QUE esta mal y, cuando puede, COMO arreglarlo, en dos
    // campos separados. Los dos van a la pantalla: tirarlos y lanzar un
    // "error 500" generico desperdicia justo el trabajo de la fase 1.
    const que = datos.error ?? `el servidor respondio ${r.status}`;
    throw new Error(datos.arreglo ? `${que} — ${datos.arreglo}` : que);
  }
  return datos as Respuesta;
}
```

Cuatro cosas que no son de relleno:

**`JSON.stringify({ messages })` manda la lista entera.** No la última pregunta: la
conversación completa, cada vez. Es lo que comprobaste con `curl` al cerrar la fase 1 —
el backend no recuerda nada, así que quien recuerda tiene que ser esto.

**`.catch(() => ({}))`.** Si el servidor devuelve algo que no es JSON —una página de
error de un proxy, una respuesta vacía— `r.json()` lanza. Sin ese `catch`, el usuario
ve un `SyntaxError: Unexpected token` en vez del error de verdad.

**`datos.arreglo` se pega al mensaje.** En la fase 1 separaste las dos mitades del
error: `error` dice qué pasó y `arreglo` dice qué hacer. Si aquí solo propagas `error`,
la pantalla dirá «no pude hablar con Ollama» y se callará justo la parte útil —
`ollama serve`— que ya habías escrito. Es el fallo más fácil de cometer y el más caro:
media hora de alguien buscando en los logs algo que el servidor ya sabía decirle.

**La URL no está escrita a mano.** Arriba del archivo:

```ts
const API = `http://${window.location.hostname}:8080`;
```

La IP pública de tu instancia cambia cada vez que el laboratorio la reinicia. Si aquí
hubiera una IP literal, la aplicación dejaría de funcionar en cada sesión — y el
síntoma sería un error de red que no se parece en nada a la causa. El puerto sí es
distinto, y por eso el navegador aplica CORS: 3000 y 8080 son dos orígenes.

### Lo que ya está escrito, y conviene leer

El resto de `App.tsx` es JSX y se lee sin explicación. Dos detalles que sí vale la pena
mirar, porque responden a preguntas que van a salir:

```tsx
        {mensajes.map((m, i) => (
          <div key={i} className={`mensaje ${m.role}`}>
```

El `role` que viene del backend se usa **como clase de CSS**. Por eso los mensajes de
quien pregunta salen a la derecha en azul y los del modelo a la izquierda: no hay un
`if` decidiéndolo, lo decide el dato. Cambiar el aspecto es tocar `styles.css` y nada
más.

```tsx
        <button type="submit" disabled={esperando || !texto.trim()}>
```

El botón se apaga solo mientras se espera. El `if (!pregunta || esperando) return` de
`mandar` parece repetirlo, y no: el botón evita el clic, la guarda evita el Enter y
cualquier otra forma de llegar ahí. Lo que protege el dato se comprueba donde está el
dato.

### Pruébalo

**En tu computadora:**

```bash
git add -A && git commit -m "fase 2: el chat" && git push
```

**En la instancia:**

```bash
git pull && ./run restart
```

Abre `http://TU-IP:3000` y escribe **dos** mensajes seguidos:

```
   [tú]      Me llamo Victor. Que es Flask, en una frase?
   [modelo]  Flask es un framework de Python ligero y rápido para desarrollo web.
   [tú]      Como me llamo?
   [modelo]  Tu nombre es Victor.
```

La segunda respuesta es la que importa. **Tu backend no recuerda nada** y aun así el
chat recuerda, porque la lista viaja entera en cada petición.

### Lo que hay que ver antes de cerrar la fase

**Míralo tú mismo.** En el navegador, `F12` → pestaña **Network** → manda un mensaje →
clic en `chat` → **Payload**. Ahí está la lista completa que salió de tu máquina:

```json
{"messages": [
  {"role": "user", "content": "Me llamo Victor. Que es Flask, en una frase?"},
  {"role": "assistant", "content": "Flask es un framework de Python..."},
  {"role": "user", "content": "Como me llamo?"}
]}
```

Cada mensaje nuevo hace la petición **más grande**. Con una API de pago eso se cobra, y
es el motivo de que los productos reales acaben recortando o resumiendo lo viejo. Hoy no
hace falta; saber que el problema existe, sí.

**Que el error del backend llega a la pantalla.** En la instancia:

```bash
sudo systemctl stop ollama
```

Manda un mensaje. En la pantalla, no en los logs:

```
No se pudo responder.
no pude hablar con Ollama en http://localhost:11434 — En la instancia:  ollama serve
```

Ese texto lo escribiste tú, en Python, en la fase 1. Atravesó un `jsonify`, un `fetch`,
un `throw` y un `useState` sin que nadie lo cambiara, y las dos mitades llegaron: qué
pasó y qué hacer. **Un error solo sirve si llega hasta quien puede arreglarlo.**

Fíjate también en la cabecera: dice *«el backend vive, pero Ollama no contesta»*, no
«el backend no responde». Son dos averías distintas y el producto sabe cuál es. Vuelve
a levantarlo:

```bash
sudo systemctl start ollama
```

**Y que el backend sigue sin memoria.** Recarga la página con `F5`. La conversación
desaparece: vivía en `useState`, en el navegador. Es la misma propiedad de la fase 1
vista desde el otro lado — y la razón de que puedas reiniciar el servidor a media clase
sin romperle la sesión a nadie.

---

## Si te atoras

**En la instancia:**

```bash
git pull            # ¿de verdad llegó lo que escribiste?
./run status        # ¿vive el backend? ¿vive Ollama?
./run salud         # ¿está mi modelo?
./run modelo        # ¿qué modelos hay instalados?
./run logs api      # el error completo del backend
./run logs web      # el error completo del frontend
```

| Síntoma | Qué pasa |
| ------- | -------- |
| `"status": "sin escribir"` | El `COMPLETA 1` sigue vacío |
| `NotImplementedError: COMPLETA 2` en los logs | El `COMPLETA 2` sigue vacío |
| `"arreglo": "ollama serve"` | Ollama no está corriendo |
| `"arreglo": "ollama pull ..."` | El modelo no está descargado |
| Tarda muchísimo | Normal. Baja `OLLAMA_MAX_TOKENS` o usa un modelo más chico |
| `COMPLETA 4` en la pantalla | El `COMPLETA 4` sigue vacío (`src/App.tsx`) |
| `COMPLETA 5` en la pantalla | El `COMPLETA 5` sigue vacío (`src/api.ts`) |
| La cabecera dice «el backend no responde» | El 3000 vive, el 8080 no. `./run logs api` |
| `Failed to fetch` en la consola del navegador | El backend no contesta, o el puerto 8080 no está abierto en el *security group* |
| Los mensajes desaparecen al responder | Leíste `mensajes` después de `setMensajes`. Es el `conPregunta` del `COMPLETA 5` |
| El botón se quedó apagado | El `setEsperando(false)` no está en un `finally` |
| `npm: command not found` | La terminal no cargó nvm. Ábrela de nuevo, o `source ~/.bashrc` |
| `web` no arranca | `bash setup/bootstrap.sh` otra vez: falta el `npm ci` |

El modelo, el tope y el timeout salen de variables de entorno, así que probar otro es una
línea y no tocar código:

```bash
OLLAMA_MODEL=llama3.2:3b OLLAMA_MAX_TOKENS=120 ./run restart
```
