/**
 * Parser do stream do endpoint POST /campaigns/{id}/action.
 *
 * O backend responde com dois content-types distintos para o mesmo endpoint:
 *
 *  - application/json — quando a validação de robustez (ADR-026) recusa
 *    a entrada *antes* de qualquer LLM. Um único `ActionEvent` com
 *    `type: "rejected"`. Turno NÃO consumido.
 *  - text/event-stream — quando o turno entra no pipeline. Um ou mais
 *    eventos `chunk` / `npc_chunk`, e fecha com `done` (ou
 *    `error_preserve_input` em falha não-fatal).
 *
 * EventSource nativo não serve (é GET-only). Usamos fetch + reader do
 * ReadableStream, e expomos um async iterator de `ActionEvent`.
 */

import { ApiError, NetworkError } from "./client";
import type { ActionEvent } from "./types";

export interface StreamActionOptions {
  signal?: AbortSignal;
}

export async function* streamAction(
  campaignId: string,
  text: string,
  options: StreamActionOptions = {},
): AsyncGenerator<ActionEvent, void, void> {
  let response: Response;
  try {
    response = await fetch(
      `/campaigns/${encodeURIComponent(campaignId)}/action`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream, application/json",
        },
        body: JSON.stringify({ text }),
        signal: options.signal,
      },
    );
  } catch (cause) {
    throw new NetworkError(
      cause instanceof Error ? cause.message : "Network error",
    );
  }

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // ignora
    }
    throw new ApiError(
      `streamAction failed with status ${response.status}`,
      response.status,
      body,
    );
  }

  const contentType = response.headers.get("content-type") ?? "";

  // Caso 1: JSON único — rejeição de robustez ou erro síncrono.
  if (contentType.includes("application/json")) {
    const event = (await response.json()) as ActionEvent;
    yield event;
    return;
  }

  // Caso 2: SSE. Lemos o stream byte a byte e quebramos em eventos.
  if (!contentType.includes("text/event-stream")) {
    throw new ApiError(
      `streamAction got unexpected content-type: ${contentType || "(none)"}`,
      response.status,
    );
  }

  if (!response.body) {
    throw new ApiError("streamAction got empty response body", response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (value) buffer += decoder.decode(value, { stream: true });

      // Cada evento SSE termina com uma linha em branco. Aceitamos \n\n
      // (canonico) e \r\n\r\n (presente em alguns proxies).
      let separator = buffer.indexOf("\n\n");
      let separatorLen = 2;
      if (separator === -1) {
        const crlf = buffer.indexOf("\r\n\r\n");
        if (crlf !== -1) {
          separator = crlf;
          separatorLen = 4;
        }
      }

      while (separator !== -1) {
        const rawEvent = buffer.slice(0, separator);
        buffer = buffer.slice(separator + separatorLen);

        const event = parseSseEvent(rawEvent);
        if (event) yield event;

        separator = buffer.indexOf("\n\n");
        separatorLen = 2;
        if (separator === -1) {
          const crlf = buffer.indexOf("\r\n\r\n");
          if (crlf !== -1) {
            separator = crlf;
            separatorLen = 4;
          }
        }
      }

      if (done) {
        // Resto de buffer sem terminador — descarta (servidor encerrou
        // sem fechar o último evento; nada útil a parsear).
        return;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseSseEvent(raw: string): ActionEvent | null {
  // Um bloco SSE pode ter linhas `data:`, `event:`, `id:`, `retry:`.
  // O backend só emite `data:` — concatenamos as linhas `data:`
  // como o protocolo manda.
  const dataLines: string[] = [];
  for (const line of raw.split(/\r?\n/)) {
    if (line.startsWith(":")) continue; // comentário SSE
    if (!line.startsWith("data:")) continue;
    dataLines.push(line.slice(5).trimStart());
  }
  if (dataLines.length === 0) return null;
  const payload = dataLines.join("\n");
  try {
    return JSON.parse(payload) as ActionEvent;
  } catch {
    return null;
  }
}
