# Hacerlo correr en tu máquina

Hasta aquí tu computadora escribía y la instancia ejecutaba. Ahora te toca hacerlo
funcionar **en tu propia máquina**, Windows o Mac.

**No hay un script que lo haga por ti, y es a propósito.** `setup/bootstrap.sh` se niega
a correr aquí:

```
Este script es para tu INSTANCIA (Ubuntu), no para tu computadora.
```

No es un descuido. Ese script instala cosas con `apt-get`, que solo existe en Ubuntu. Lo
que vas a hacer es **sus mismos pasos, a mano**, en tu sistema. Y ese es el ejercicio: a
estas alturas ya sabes qué necesita el producto para funcionar; averiguar cómo se
instala eso en *tu* sistema es la prueba de que lo entendiste.

---

## Lo que hace falta, y da igual el sistema

Son cuatro cosas. Las mismas cuatro que instaló el bootstrap en la instancia:

```
   1. Python          para correr Flask
   2. un entorno      .venv/, donde viven las dependencias de ESTE proyecto
   3. Flask y demás   backend/requirements.txt
   4. Ollama          el servidor del modelo, y el modelo
```

Lo que cambia entre sistemas es **cómo se llama cada comando y dónde deja los archivos**,
no qué se instala.

> **Node no está en la lista.** Solo lo necesitas si además quieres el chat; al final hay
> una sección para eso. El backend no lo usa.

---

## Mac

### 1. Python: ya lo tienes

```bash
python3 --version
```

macOS trae Python. En una Mac recién salida de fábrica responde `Python 3.9.6`, y
**sirve**: Flask 3.0 funciona con él. No instales nada todavía.

Ojo a un detalle que confunde: en Mac el comando es `python3`, no `python`. `python` a
secas no existe.

### 2. El entorno virtual

Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
```

Eso crea `.venv/` con su propio Python y su propio pip. Es lo mismo que hay en la
instancia y por la misma razón: las dependencias de este proyecto no se mezclan con las
de tu sistema.

### 3. Las dependencias

```bash
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r backend/requirements.txt
```

Fíjate en que **no activamos nada**. Podrías hacer `source .venv/bin/activate`, pero
llamar a `.venv/bin/pip` directamente es lo que hace `./run`, y así no hay una
activación que olvidar. Una fuente de confusión menos.

> **`NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+`**
>
> Vas a ver ese aviso cada vez que arranques. El Python de macOS viene compilado contra
> LibreSSL y urllib3 se queja. **Es un aviso, no un error**: todo funciona. Si te molesta
> ver ruido, instala un Python propio con Homebrew y rehaz el entorno:
>
> ```bash
> brew install python@3.12
> rm -rf .venv && /opt/homebrew/bin/python3.12 -m venv .venv
> ```

### 4. Ollama

Bájalo de **[ollama.com/download](https://ollama.com/download)** y arrástralo a
Aplicaciones. O con Homebrew:

```bash
brew install ollama
```

Ábrelo. Se queda como un icono en la barra de arriba y **escucha solo en el 11434**, el
mismo puerto que en la instancia — por eso no hay que cambiar ni una línea del código.
Compruébalo:

```bash
curl http://localhost:11434/api/tags
```

Y baja el modelo (~1 GB):

```bash
ollama pull qwen2.5:1.5b
```

### 5. Arráncalo

```bash
./run start
./run salud
```

`./run` **sí funciona en tu Mac**, en cuanto existe `.venv/`. Lo que rechazaba antes era
arrancar sin entorno, no la Mac.

```json
{"keep_alive": "30m", "max_tokens": 180, "modelo": "qwen2.5:1.5b", "status": "ok"}
```

Y la prueba de verdad:

```bash
curl -s -X POST http://localhost:8080/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Di hola en tres palabras."}]}'
```

---

## Windows

Todo esto va en **Git Bash**, no en PowerShell. Ya lo configuraste en el setup; si no,
`Ctrl+Shift+P` → **Terminal: Select Default Profile** → **Git Bash**.

### 1. Python: hay que instalarlo

Windows **no trae Python**. Bájalo de
**[python.org/downloads](https://www.python.org/downloads/)** y en la primera pantalla
del instalador marca la casilla:

```
   [x] Add python.exe to PATH
```

**Esa casilla es la mitad del trabajo.** Si se te olvida, el instalador termina bien y
después ningún comando encuentra Python. Se arregla reinstalando y marcándola.

Cierra la terminal, abre otra, y:

```bash
python --version
```

En Windows el comando es `python`, **no `python3`**. Es justo al revés que en Mac.

> **Si `python` te abre la Microsoft Store**, estás viendo un atajo que Windows trae de
> fábrica y que no es Python. Significa que la casilla del PATH no quedó marcada.
> Desactívalo en **Configuración → Aplicaciones → Alias de ejecución de aplicaciones**, o
> reinstala Python marcándola.

### 2. El entorno virtual

```bash
python -m venv .venv
```

**Aquí está la diferencia que más confunde.** Compara:

```
   Mac / Linux        .venv/bin/python
   Windows            .venv/Scripts/python.exe
```

No es un capricho: es como Python crea los entornos en cada sistema. Toda instrucción
que veas por ahí con `.venv/bin/...` hay que traducirla a `.venv/Scripts/...`.

### 3. Las dependencias

```bash
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/pip install -r backend/requirements.txt
```

### 4. Ollama

Baja **OllamaSetup.exe** de
**[ollama.com/download](https://ollama.com/download)** e instálalo. Queda corriendo en la
bandeja del sistema, junto al reloj, y escucha en el 11434 como en todas partes.

```bash
curl http://localhost:11434/api/tags
ollama pull qwen2.5:1.5b
```

### 5. Arráncalo

**En Windows no uses `./run`.** El script busca el intérprete en `.venv/bin/python`, que
en tu sistema no existe — está en `Scripts/`. Arranca el backend directamente:

```bash
.venv/Scripts/python backend/app.py
```

Vas a ver:

```
Ollama en http://localhost:11434 · modelo qwen2.5:1.5b · tope 180 tokens
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:8080
```

**Esa terminal se queda ocupada**: ahí está corriendo tu servidor. Para probarlo abre
**otra** terminal:

```bash
curl http://localhost:8080/api/health
```

Para detenerlo, `Ctrl+C` en la primera.

> Que `./run` no te sirva no es un problema: es exactamente lo que el script hacía por ti.
> Levantar el proceso, saber en qué puerto escucha y cómo pararlo — ahora lo haces tú.

---

## Las diferencias, juntas

| | Mac | Windows |
| --- | --- | --- |
| Terminal | la que traiga VS Code | **Git Bash**, no PowerShell |
| ¿Trae Python? | sí, 3.9.6 | no, se instala de python.org |
| El comando | `python3` | `python` |
| El intérprete del entorno | `.venv/bin/python` | `.venv/Scripts/python` |
| Activar (si quieres) | `source .venv/bin/activate` | `source .venv/Scripts/activate` |
| Ollama | app en la barra de arriba | app en la bandeja del sistema |
| Arrancar | `./run start` | `.venv/Scripts/python backend/app.py` |

**Lo que NO cambia:** el puerto 11434 de Ollama, el 8080 del backend, `requirements.txt`,
y ni una línea de `backend/app.py`. Ese es el punto — el código no sabe en qué sistema
está.

---

## Lo que vas a notar: la velocidad

La instancia es una t2.large: 2 vCPU y **sin GPU**. Tu laptop probablemente tiene una.

Medido con el mismo modelo y el mismo método —los tokens que genera Ollama dividido
entre el tiempo que dice que tardó, sin contar la carga inicial:

```
   t2.large (2 vCPU, sin GPU)      5.8 tokens/s
   MacBook Pro M4 Pro            150.7 tokens/s
```

Veintiséis veces. Tu número será otro —un M1 va más despacio que un M4, y un portátil
Windows sin GPU dedicada se parecerá más a la instancia—, pero la conclusión aguanta:
**el modelo no es lo lento; la máquina sin GPU lo es.**

Compruébalo tú:

```bash
curl -s http://localhost:11434/api/chat -d '{
  "model":"qwen2.5:1.5b",
  "messages":[{"role":"user","content":"Explica que es una API REST en un parrafo."}],
  "stream":false}' | python3 -c "
import sys,json; d=json.load(sys.stdin)
n, ns = d['eval_count'], d['eval_duration']
print(f'{n} tokens en {ns/1e9:.1f}s -> {n/(ns/1e9):.1f} tokens/s')"
```

(En Windows, `python` en vez de `python3` en la última línea.)

Esto es una decisión de arquitectura, no una curiosidad. El mismo producto es cómodo en
una máquina con GPU e incómodo en una sin ella, **sin cambiar una línea de código**. Es
el argumento de por qué en producción esto correría en una instancia con GPU, o contra
una API, y por qué esa decisión se toma midiendo y no opinando.

---

## Si además quieres el chat

Necesitas Node. Igual que arriba: la LTS activa, **no** la más nueva.

**Mac** — con [nvm](https://github.com/nvm-sh/nvm) o bajando el instalador de
[nodejs.org](https://nodejs.org/) (elige la que diga **LTS**):

```bash
brew install node@24        # o el instalador de nodejs.org
```

**Windows** — el instalador `.msi` de [nodejs.org](https://nodejs.org/), el de la
columna **LTS**.

En los dos, desde la carpeta del proyecto:

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:3000`. El frontend deduce la dirección del backend de dónde se
cargó la página, así que en local apunta solo a `localhost:8080`, sin tocar nada.

---

## Si te atoras

**`python: command not found` (Windows).**
La casilla del PATH. Reinstala Python marcándola, y abre una terminal nueva.

**`No module named flask`.**
Estás usando el Python del sistema y no el del entorno. El comando lleva la ruta entera:
`.venv/bin/python` en Mac, `.venv/Scripts/python` en Windows.

**`error: externally-managed-environment`.**
Un `pip install` fuera del entorno. Mismo arreglo: la ruta completa al pip del `.venv`.

**`Address already in use` / `[Errno 48]`.**
Ya tienes algo en el 8080 — casi siempre otro backend tuyo de antes. En Mac,
`./run stop`. En Windows, `Ctrl+C` en la terminal donde corría.

**`no pude hablar con Ollama en http://localhost:11434`.**
Ollama no está abierto. Ábrelo desde Aplicaciones (Mac) o el menú Inicio (Windows), y
comprueba con `curl http://localhost:11434/api/tags`.

**`model "qwen2.5:1.5b" not found`.**
Falta bajarlo en **esta** máquina: `ollama pull qwen2.5:1.5b`. El de la instancia no
cuenta.

**La primera respuesta tarda muchísimo y las demás no.**
Es la carga del modelo a memoria, no la generación. Lo mismo que en la instancia, y la
razón de que el backend mande `keep_alive`.
