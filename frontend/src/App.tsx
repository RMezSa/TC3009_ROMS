import { useEffect, useRef, useState, type FormEvent } from "react";
import { enviar, salud, type Mensaje, type Salud } from "./api";

export default function App() {
  // LA CONVERSACION VIVE AQUI.
  //
  // El backend no recuerda nada: en cada peticion le mandas la lista completa.
  // Eso que parece un rodeo es lo que hace que un chat "recuerde", y es lo que
  // comprobaste con curl al cerrar la fase 1.
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [texto, setTexto] = useState("");
  const [esperando, setEsperando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Tres estados posibles, no dos. Puede estar caido el backend O puede estar
  // caido Ollama, y son arreglos distintos: decirle "no responde" a los dos
  // manda a media clase a mirar el sitio equivocado.
  const [estado, setEstado] = useState<Salud | null>(null);

  const finRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    salud()
      .then(setEstado)
      .catch(() => setEstado(null));
  }, []);

  // Bajar solo al final cuando llega algo nuevo.
  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes, esperando]);

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

  return (
    <div className="pagina">
      <header>
        <h1>Chat</h1>
        <p>
          {estado === null
            ? "el backend no responde"
            : estado.status === "ok" && estado.modelo
              ? `modelo ${estado.modelo}`
              : "el backend vive, pero Ollama no contesta"}
        </p>
      </header>

      <div className="conversacion">
        {mensajes.length === 0 && !esperando && (
          <p className="vacio">Escribe algo abajo para empezar.</p>
        )}

        {mensajes.map((m, i) => (
          <div key={i} className={`mensaje ${m.role}`}>
            <span className="quien">{m.role === "user" ? "tú" : "modelo"}</span>
            <div className="texto">{m.content}</div>
          </div>
        ))}

        {esperando && (
          <div className="mensaje assistant">
            <span className="quien">modelo</span>
            <div className="texto pensando">pensando…</div>
          </div>
        )}

        {error && (
          <div className="aviso-error">
            <strong>No se pudo responder.</strong>
            <p>{error}</p>
          </div>
        )}

        <div ref={finRef} />
      </div>

      <form className="entrada" onSubmit={mandar}>
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Escribe tu pregunta"
          disabled={esperando}
          autoFocus
        />
        <button type="submit" disabled={esperando || !texto.trim()}>
          {esperando ? "…" : "Enviar"}
        </button>
      </form>
    </div>
  );
}
