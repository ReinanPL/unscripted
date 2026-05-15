/**
 * Tipos espelhados dos schemas Pydantic do backend.
 *
 * Quando o backend muda um schema, este arquivo é a fonte de verdade do
 * lado do cliente. Manter alinhado com:
 *   backend/app/api/schemas.py
 *   backend/app/state/models.py
 *   backend/app/agents/contracts.py
 *   backend/app/agents/robustness.py
 *   backend/app/rules/{dice,checks,proposals}.py
 */

// ===== Personagem e estado =====

export type CharacterClass = "guerreiro" | "paladino";

export interface CharacterAttributes {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

export interface Character {
  name: string;
  character_class: CharacterClass;
  level: number;
  hp_current: number;
  hp_max: number;
  attributes: CharacterAttributes;
  skills: string[];
  equipment: string[];
}

export interface InventoryItem {
  name: string;
  description: string;
  quantity: number;
}

export interface Location {
  id: string;
  name: string;
  description: string;
}

export interface Flags {
  objectives_completed: string[];
  events_occurred: string[];
  locations_revealed: string[];
}

export interface HistoryEntry {
  turn: number;
  player_action: string;
  narration: string;
  timestamp: string;
}

// ===== Endpoints REST =====

export interface CampaignCreateRequest {
  character: CharacterClass;
}

export interface CampaignCreateResponse {
  campaign_id: string;
}

export interface CampaignStateResponse {
  campaign_id: string;
  character: Character;
  inventory: InventoryItem[];
  location: Location;
  flags: Flags;
}

export interface CampaignLogResponse {
  campaign_id: string;
  history: HistoryEntry[];
}

export interface TurnTraceResponse {
  campaign_id: string;
  turn_number: number;
  trace: TurnTrace;
}

// Grafo (endpoint ainda a implementar — ADR-038).
export interface GraphNode {
  id: string;
  name: string;
  position: { x: number; y: number };
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphResponse {
  campaign_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  current: string;
}

// ===== SSE do endpoint /action =====

export type ActionEventType =
  | "chunk"
  | "npc_chunk"
  | "done"
  | "error"
  | "error_preserve_input"
  | "rejected";

export interface ActionEvent {
  type: ActionEventType;
  text: string;
  npc_id?: string | null;
  turn_number?: number | null;
  category?: string | null;
}

// ===== Trace / pensamento do mestre =====

export type RobustnessCategory =
  | "declaracao_de_resultado"
  | "injecao"
  | "conteudo_proibido";

export interface RobustnessVerdict {
  ok: boolean;
  category?: RobustnessCategory | null;
  reason: string;
  matched: string;
}

export interface RollResult {
  notation: string;
  rolls: number[];
  modifier: number;
  total: number;
  advantage: boolean;
  disadvantage: boolean;
}

export interface CheckResult {
  success: boolean;
  roll_total: number;
  difficulty: number;
  margin: number;
}

export interface RollOutcome {
  roll: RollResult;
  check: CheckResult;
}

export interface ItemRemoveProposal {
  name: string;
  quantity: number;
}

export interface ConsequenceProposal {
  hp_delta?: number | null;
  items_added: InventoryItem[];
  items_removed: ItemRemoveProposal[];
  new_location?: Location | null;
  events_occurred: string[];
  objectives_completed: string[];
}

export interface Ruling {
  precisa_rolagem: boolean;
  pericia?: string | null;
  dificuldade?: number | null;
  notacao_dado: string;
  motivo_dificuldade: string;
  consequencia?: ConsequenceProposal | null;
  consequencia_sucesso?: ConsequenceProposal | null;
  consequencia_falha?: ConsequenceProposal | null;
  npc_to_react?: string | null;
}

export interface RetrievalSnippet {
  corpus: string;
  source: string;
  content: string;
}

export interface TurnTrace {
  turn: number;
  player_action: string;
  robustness: RobustnessVerdict;
  retrieval_rules: RetrievalSnippet[];
  retrieval_lore: RetrievalSnippet[];
  ruling?: Ruling | null;
  roll_outcome?: RollOutcome | null;
  consequence_applied?: ConsequenceProposal | null;
  narration: string;
  npc_reaction?: string | null;
  npc_id?: string | null;
  error?: string | null;
}
