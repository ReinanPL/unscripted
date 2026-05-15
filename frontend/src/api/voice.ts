/**
 * Cliente dos endpoints de voz (POST /voice/stt e /voice/tts).
 *
 * A v1 fala com um provider stub que devolve payloads vazios — a UI
 * exercita o fluxo sem áudio real circular. A implementação concreta
 * é v2 (ADR-014). A API aceita base64 para evitar FormData no frontend.
 */

import { request } from "./client";

export interface SttResponse {
  text: string;
}

export interface TtsResponse {
  audio_base64: string;
  mime_type: string;
}

export async function sttFromBlob(blob: Blob): Promise<SttResponse> {
  const audio_base64 = await blobToBase64(blob);
  return request<SttResponse>("/voice/stt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ audio_base64, mime_type: blob.type }),
  });
}

export async function tts(
  text: string,
  voice = "",
): Promise<TtsResponse> {
  return request<TtsResponse>("/voice/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice }),
  });
}

async function blobToBase64(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  // Loop manual evita estouro de stack em blobs grandes (apply spread).
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
