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
  // COMPLETA 5 — habla con el backend.
  //
  // POST a `${API}/api/chat` con:
  //
  //   method:  "POST"
  //   headers: {"Content-Type": "application/json"}
  //   body:    JSON.stringify({ messages })
  //
  // Mandas la conversacion ENTERA, no solo la ultima pregunta. El backend no
  // recuerda nada --lo decidiste asi en la fase 1-- de modo que quien recuerda
  // es esto. Si mandaras solo el ultimo mensaje, el chat no tendria memoria.
  //
  // Y cuando la respuesta no sea ok, lanza un Error con lo que dice el
  // backend. Ojo a que son DOS campos: "error" dice que paso y "arreglo" dice
  // que hacer. Los dos tienen que llegar a la pantalla -- quedarte solo con el
  // primero es callar justo la parte util, que ya escribiste en la fase 1.
  throw new Error(
    `COMPLETA 5: falta la llamada a ${API}/api/chat, en src/api.ts ` +
      `(iba a mandar ${messages.length} mensaje(s))`,
  );
}

export async function salud(): Promise<Salud> {
  const r = await fetch(`${API}/api/health`);
  return r.json();
}
