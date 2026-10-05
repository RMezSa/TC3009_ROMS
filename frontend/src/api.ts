// La costura con el backend. El unico archivo del frontend que sabe que existe
// un servidor: si mañana cambia la URL o el formato, se cambia aqui y nada mas.
//
// Hay 1 COMPLETA en este archivo (el ultimo).

// Un mensaje de la conversacion.
//
// Este tipo NO es decoracion: es el contrato con el backend, escrito de forma
// que TypeScript lo revise. Si mandas un role que no existe, el error sale
// mientras escribes, no cuando el modelo devuelve algo raro.
export type Mensaje = {
  role: "user" | "assistant";
  content: string;
};

// Lo que responde POST /api/chat. Es el jsonify() que escribiste en la fase 1,
// mirado desde el otro lado.
export type Respuesta = {
  respuesta: string;
  modelo: string;
  tokens: number;
};

// Lo que responde GET /api/health: "ok" o "degradado", y que modelo hay.
export type Salud = {
  status: string;
  modelo?: string;
};

// La direccion del backend se DERIVA de donde se cargo esta pagina.
//
// No esta escrita a mano a proposito: la IP publica de la instancia cambia cada
// vez que el laboratorio la reinicia. Si aqui hubiera una IP literal, la
// aplicacion dejaria de funcionar en cada sesion nueva.
//
// El puerto SI es distinto: el frontend vive en el 3000 y el backend en el
// 8080. Puertos distintos = origenes distintos = el navegador aplica CORS, y
// por eso el backend trae CORS(app).
const API = `http://${window.location.hostname}:8080`;

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

export async function salud(): Promise<Salud> {
  const r = await fetch(`${API}/api/health`);
  return r.json();
}
