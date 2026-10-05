# Antes de empezar

Quince minutos, y se hace **una sola vez** para toda la parte 2.

---

## Cómo se trabaja en esta parte

En la parte 1 cada quien hizo un *fork*. Aquí no. El fork ata tu repositorio al del curso, y
cuando algo se desincroniza —que pasa— arreglarlo es complicado justo cuando menos tiempo
tienes.

Esta vez tu repositorio es **tuyo, desde cero**:

```
   Repo del curso            Tu repositorio             Tu instancia
   ──────────────            ──────────────             ────────────
   lo bajas una vez  ──▶  escribes en VS Code  ──push──▶  lo clonas
   (guías y esqueleto)         y haces push              y lo pruebas
```

Tres cosas que esto cambia respecto a la parte 1:

| | |
|---|---|
| **No hay fork** | Tu repositorio no depende del mío. Nada se desincroniza |
| **Tu repositorio es público** | Para que la instancia pueda clonarlo sin contraseñas ni tokens |
| **La instancia clona el tuyo** | No el del curso. Ahí pruebas lo que escribiste |

---

## 1. En tu computadora

Tres cosas, y **nada más**:

| Qué | Dónde | Para qué |
| --- | ----- | -------- |
| **git** | [git-scm.com](https://git-scm.com/downloads) | mover tu código a GitHub |
| **VS Code** | [code.visualstudio.com](https://code.visualstudio.com/) | escribir el código |
| **Cuenta de GitHub** | [github.com](https://github.com/) | donde vive tu repositorio |

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu-correo@tec.mx"
```

### Lo que NO instalas en tu computadora

**Python. Node. Ollama. Ninguno.**

Tu máquina escribe el código; la instancia lo ejecuta. Es lo mismo de la parte 1 y aquí
importa aún más, porque Ollama y el modelo son un gigabyte que solo tiene sentido donde corre
el producto.

Da exactamente igual si usas Windows, Mac o Linux: lo que se ejecuta corre en Ubuntu, igual
para todos. Esa es media razón de que el curso funcione con 30 laptops distintas.

> Si ya tienes Python o Node instalados, no estorban — pero no los vamos a usar. Y si intentas
> correr `./run start` o `bash setup/bootstrap.sh` en tu computadora, los dos te van a decir
> que ese no es su sitio, en vez de fallar con un error críptico.

**Por ahora.** Al final del módulo vas a tener que hacer correr todo esto en tu propia
máquina, y va a ser un ejercicio, no un paso del setup: no habrá un script que lo haga por ti.
Para entonces vas a saber exactamente qué necesita el producto para funcionar — y averiguar
cómo instalarlo en *tu* sistema es justo la prueba de que lo entendiste. Cuando llegues ahí,
el mapa está en **[en-tu-maquina.md](en-tu-maquina.md)**.

### Si usas Windows: Git Bash como terminal de VS Code

**No es opcional.** VS Code en Windows abre PowerShell, y los comandos de este curso están
escritos para `bash`. En PowerShell, `./run start` falla así:

```
Error al ejecutar el programa 'run': La operación que se ha intentado no está permitida
```

Ya tienes bash: viene con Git for Windows. Solo hay que decirle a VS Code que lo use.

1. `Ctrl+Shift+P` → **Terminal: Select Default Profile** → **Git Bash**
2. Cierra la terminal abierta y abre una nueva

Compruébalo con `echo $SHELL`: tiene que terminar en `bash`.

---

## 2. Crea tu repositorio

En GitHub, **New repository**:

- Nombre: el que quieras. `TC3009-Part2` está bien.
- **Público.** No es un detalle: tu instancia lo va a clonar, y no tiene credenciales de
  GitHub. Un repositorio privado le pediría usuario y contraseña, y se quedaría colgado.
- **Sin** README, sin `.gitignore`, sin licencia. Vacío del todo.

Copia su URL. La vas a usar en el siguiente paso.

> **¿Y si no quiero que mi código sea público?** Entonces tendrías que generar un token de
> acceso personal y pegarlo en la instancia — una credencial tuya viviendo en una máquina
> compartida y desechable. Para este curso no vale la pena. Tu código no tiene secretos: las
> claves y las direcciones salen de variables de entorno, nunca del repositorio.

---

## 3. Baja el contenido del curso

Hay dos formas. **La primera es mejor** y solo tiene una línea más.

### Opción A — clonar y reapuntar (recomendada)

```bash
git clone https://github.com/vsosahdz/TC3009-Part2-2026.git
cd TC3009-Part2-2026

git remote rename origin curso
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git
git push -u origin main
```

Cuatro comandos, y te dejan con lo mejor de los dos mundos: tu repositorio es tuyo, y
`curso` sigue ahí para traer correcciones sin depender de nada.

Compruébalo:

```bash
git remote -v
```

```
curso    https://github.com/vsosahdz/TC3009-Part2-2026.git (fetch)
origin   https://github.com/TU-USUARIO/TU-REPO.git (push)
```

### Opción B — el ZIP

Si te perdiste con lo anterior: en la página del repo del curso, **Code → Download ZIP**.
Descomprime, entra a la carpeta, y:

```bash
git init
git add -A
git commit -m "material del curso"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git
git push -u origin main
```

Funciona igual, con una diferencia que se nota en la siguiente sección: **tu repositorio no
comparte historia con el mío**, así que traer material nuevo se hace de otra forma.

---

## Traer material nuevo del curso

**Esto lo vas a usar varias veces durante el módulo**, porque el material llega por partes:
el backend primero, el frontend después. No hace falta volver a clonar nada ni empezar de
cero — y sobre todo, **no vas a perder el código que ya escribiste**.

Hay dos formas. **Empieza por la primera**: funciona igual para todo el mundo, sin importar
cómo bajaste el curso ni qué remotos tengas.

### Forma 1 — descargar y copiar (la que siempre funciona)

**1. Baja el curso otra vez.** En
[github.com/vsosahdz/TC3009-Part2-2026](https://github.com/vsosahdz/TC3009-Part2-2026),
botón verde **Code** → **Download ZIP**. Descomprímelo. Te deja una carpeta llamada
`TC3009-Part2-2026-main`.

**2. Copia a tu proyecto las carpetas del curso.** Puedes arrastrarlas en el explorador de
archivos, o desde la terminal, estando en tu proyecto:

```bash
cp -r ~/Downloads/TC3009-Part2-2026-main/frontend .
cp -r ~/Downloads/TC3009-Part2-2026-main/docs .
cp -r ~/Downloads/TC3009-Part2-2026-main/setup .
cp    ~/Downloads/TC3009-Part2-2026-main/run .
```

> **`backend/` NO se copia.** Esa carpeta es tuya: ahí están los `COMPLETA` que escribiste.
> Copiarla encima borraría tu trabajo y te devolvería el esqueleto vacío. Es el único error
> grave que se puede cometer en este paso, así que léelo dos veces.
>
> Las otras cuatro sí se copian enteras sin miedo, porque son material del curso y tú no las
> editas: `frontend/` es el esqueleto nuevo, `docs/` son las guías, `setup/` y `run` son las
> herramientas.

**3. Súbelo a tu repositorio**, desde tu proyecto:

```bash
git add -A
git commit -m "material nuevo del curso"
git push
```

**4. Y tráelo a la instancia:**

```bash
git pull
bash setup/bootstrap.sh    # por si el material nuevo necesita algo que no tenías
./run restart
```

Comprueba antes de subir que no te llevas por delante tu backend:

```bash
git status
```

Si en la lista aparece `backend/app.py`, copiaste de más. Recupéralo con
`git checkout -- backend/app.py` y vuelve a hacer el `git add`.

### Forma 2 — con git, si te sientes cómodo

Hace lo mismo en dos comandos y sin bajar nada, pero depende de cómo montaste tu
repositorio. Mira qué remotos tienes:

```bash
git remote -v
```

**Si ves uno llamado `curso`** (seguiste la opción A):

```bash
git fetch curso
git merge curso/main --no-edit
```

Git junta lo nuevo del curso con lo tuyo. Lo que tú escribiste y yo no toqué se queda igual;
lo que yo añadí aparece; y si los dos tocamos el mismo archivo en sitios distintos —lo
normal— los combina sin preguntarte.

**Si no ves `curso`** (bajaste el ZIP), tu repositorio y el mío no comparten historia y un
`merge` ni siquiera arranca: `fatal: refusing to merge unrelated histories`. Trae los
archivos por ruta:

```bash
git remote add curso https://github.com/vsosahdz/TC3009-Part2-2026.git   # una sola vez
git fetch curso
git checkout curso/main -- frontend/ docs/ setup/ run README.md
```

En los dos casos, termina con `git add -A && git commit -m "..." && git push`.

> **Si ves esto:**
>
> ```
> error: Your local changes to the following files would be overwritten by merge:
> 	run
> Please commit your changes or stash them before you merge.
> ```
>
> Tienes cambios sin guardar en un archivo que el curso también cambió. Git **no hizo
> nada** — te está protegiendo. Guarda lo tuyo y repite:
>
> ```bash
> git add -A && git commit -m "lo mio"
> git merge curso/main --no-edit
> ```

---

## 4. Tu instancia

La misma t2.large de siempre. Si la tienes de la parte 1, sáltate crearla.

**En la instancia**, clona **tu** repositorio —no el del curso— y aprovisiona:

```bash
cd ~
git clone https://github.com/TU-USUARIO/TU-REPO.git
cd TU-REPO
bash setup/bootstrap.sh
```

Una instancia recién creada **no trae nada**: ni Python, ni Node, ni Ollama. El bootstrap
instala las cinco capas y comprueba cada una antes de seguir:

```
  0 · espacio en disco        avisa si no caben los ~2.5 GB que vienen
  1 · paquetes del sistema    python3, python3-venv, git, curl, lsof
  2 · entorno virtual         .venv/ dentro del proyecto
  3 · dependencias Python     Flask, CORS, requests
  4 · Node y el frontend      Node 24 (LTS) con nvm, y npm ci
  5 · Ollama y el modelo      el servidor y ~1 GB de pesos
```

Termina con una comprobación de las cuatro, y si algo quedó a medias lo dice y puedes volver
a correrlo: no reinstala lo que ya está.

**La descarga del modelo es de ~1 GB**, así que hazlo antes de la clase, no durante.

> **Por qué un entorno virtual y no `pip install` a secas.** Ubuntu 24.04 protege el Python
> del sistema: un `pip install` fuera de un entorno se niega con
> `externally-managed-environment`. No es un estorbo, es correcto — las dependencias de tu
> proyecto no deben mezclarse con las del sistema operativo. Por eso todo vive en `.venv/`, y
> por eso `./run` llama a `.venv/bin/python` directamente en vez de pedirte que actives nada.
> Una activación olvidada es una fuente de confusión menos.
>
> **Si el disco se queda corto**, el volumen por defecto de una instancia nueva son 8 GB y
> aquí caben justos. El paso 0 te avisa antes de empezar a bajar, no a la mitad.

Luego:

```bash
./run start
./run salud
```

---

## El ciclo de trabajo

Es el mismo de la parte 1, cambiando de dónde clona la instancia:

```
   1. Editas en VS Code, en tu computadora
   2. git add -A && git commit -m "..." && git push
   3. En la instancia:  git pull && ./run restart
```

**Nunca edites en la instancia.** Lo que escribas ahí lo pisa el siguiente `git pull`, y no
está en tu repositorio, así que no cuenta como entregado.

---

## 5. Comprueba antes de la clase

- [ ] `git --version` responde
- [ ] Tu repositorio existe en GitHub, es **público**, y tiene el material
- [ ] `git remote -v` muestra `origin` (el tuyo) y, si usaste la opción A, `curso`
- [ ] En la instancia: `./run salud` dice algo
- [ ] En la instancia: `ollama list` muestra tu modelo
- [ ] **En Windows:** `echo $SHELL` termina en `bash`

---

## Problemas comunes

**`Support for password authentication was removed` al hacer push.**
GitHub no acepta contraseña. Usa un token de acceso personal como contraseña, o configura SSH.
Se hace una vez.

**La instancia se queda colgada pidiendo `Username for 'https://github.com'`.**
Tu repositorio es privado. Hazlo público en **Settings → General → Change visibility**.

**`./run` no se reconoce (Windows).**
Estás en PowerShell. Paso 1, Git Bash.

**`./run start` en mi computadora dice «esto se corre en la INSTANCIA».**
Correcto, no es un error. Tu máquina no ejecuta nada: edita, hace `commit` y `push`. Lo que
corre, corre en la instancia.

**`bash setup/bootstrap.sh` en mi Mac dice lo mismo.**
Igual. Ese script instala Ubuntu-cosas con `apt-get`; en tu Mac no tiene nada que hacer.

**`./run salud` dice que Ollama no responde.**
En la instancia: `ollama serve &`. Si acabas de reiniciarla, el servicio puede tardar.

**El modelo tarda muchísimo.**
Es una t2.large sin GPU: normal. La guía explica qué hacer con eso — y resulta que la
respuesta no es «un modelo más rápido».
