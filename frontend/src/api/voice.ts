/**
 * Cliente dos endpoints de voz (POST /voice/stt e /voice/tts).
 *
 * Providers reais: Groq Whisper (STT) e OpenAI gpt-4o-mini-tts (TTS),
 * configurados no backend via `.env` (ADR-047). O cliente fala JSON
 * com base64 para evitar FormData e simplificar o lado do navegador.
 *
 * O `tts()` cru devolve o base64; `ttsToBlob()` é o atalho usado pelo
 * Play.tsx — decodifica direto para Blob, que entra no `useAudioQueue`.
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

export async function tts(text: string, voice = ""): Promise<TtsResponse> {
  return request<TtsResponse>("/voice/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice }),
  });
}

/**
 * Variante conveniência: pede o TTS e devolve um Blob pronto pro
 * <audio> tocar. Retorna `null` se o backend devolveu áudio vazio
 * (stub ou texto vazio do lado dele).
 */
export async function ttsToBlob(
  text: string,
  voice = "",
): Promise<Blob | null> {
  const response = await tts(text, voice);
  if (!response.audio_base64) return null;
  const bytes = base64ToBytes(response.audio_base64);
  const mime = response.mime_type || "audio/mpeg";
  return new Blob([new Uint8Array(bytes)], { type: mime });
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

function base64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    out[i] = binary.charCodeAt(i);
  }
  return out;
}
