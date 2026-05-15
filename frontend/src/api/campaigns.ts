/**
 * Funções tipadas dos endpoints REST de campanha.
 *
 * O endpoint /action é SSE e fica em ./sse — não tem cara de função
 * que retorna JSON simples, então merece módulo próprio.
 */

import { request } from "./client";
import type {
  CampaignCreateRequest,
  CampaignCreateResponse,
  CampaignLogResponse,
  CampaignStateResponse,
  GraphResponse,
  TurnTraceResponse,
} from "./types";

export async function createCampaign(
  body: CampaignCreateRequest,
): Promise<CampaignCreateResponse> {
  return request<CampaignCreateResponse>("/campaigns", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getCampaignState(
  campaignId: string,
): Promise<CampaignStateResponse> {
  return request<CampaignStateResponse>(
    `/campaigns/${encodeURIComponent(campaignId)}/state`,
  );
}

export async function getCampaignLog(
  campaignId: string,
): Promise<CampaignLogResponse> {
  return request<CampaignLogResponse>(
    `/campaigns/${encodeURIComponent(campaignId)}/log`,
  );
}

export async function getTurnTrace(
  campaignId: string,
  turnNumber: number,
): Promise<TurnTraceResponse> {
  return request<TurnTraceResponse>(
    `/campaigns/${encodeURIComponent(campaignId)}/turn/${turnNumber}/trace`,
  );
}

export async function getCampaignGraph(
  campaignId: string,
): Promise<GraphResponse> {
  return request<GraphResponse>(
    `/campaigns/${encodeURIComponent(campaignId)}/graph`,
  );
}
