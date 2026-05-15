#!/usr/bin/env bash
# smoke_phase5_emboscada.sh
# Reproduz o encontro-padrão estilo emboscada do PRD §5, agora encarnado
# como o encontro emboscada_clareira do capítulo 1. Valida o loop completo:
# Referee → rolagem → consequência → Narrator → reação de NPC → trace.
#
# Pré-requisitos:
#   docker compose up -d (backend + postgres no ar; ingestão executada no startup)
#   capítulo 1 finalizado em content/chapters/chapter-01/chapter.yaml
set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "=== Smoke Fase 5: encontro emboscada (cenário-canônico PRD §5) ==="
echo ""

echo "[1/4] Criando campanha (Guerreiro)..."
RESPONSE=$(curl -sf -X POST "$BASE_URL/campaigns" \
    -H "Content-Type: application/json" \
    -d '{"character": "guerreiro"}')
CAMPAIGN_ID=$(echo "$RESPONSE" | python3 -c "import sys,json;print(json.load(sys.stdin)['campaign_id'])")
echo "      campaign_id: $CAMPAIGN_ID"

run_action() {
    local label="$1"
    local action="$2"
    echo ""
    echo "[$label] Ação: \"$action\""
    curl -sN -X POST "$BASE_URL/campaigns/$CAMPAIGN_ID/action" \
        -H "Content-Type: application/json" \
        -d "{\"text\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$action")}" \
        --max-time 120 | python3 -c "
import sys, json
narration = []
npc = []
done_turn = None
err = None
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('data:'):
        continue
    evt = json.loads(line[5:].strip())
    t = evt['type']
    if t == 'chunk':
        narration.append(evt['text'])
    elif t == 'npc_chunk':
        npc.append(evt['text'])
    elif t == 'done':
        done_turn = evt.get('turn_number')
    elif t == 'error_preserve_input':
        err = evt['text']
    elif t == 'rejected':
        err = f'rejected ({evt.get(\"category\")}): {evt.get(\"text\")}'
narration_text = ''.join(narration).strip()
npc_text = ''.join(npc).strip()
if err:
    print('      ERRO:', err)
else:
    print(f'      done turno={done_turn}, narração={len(narration_text)} chars, npc={len(npc_text)} chars')
    print('      --- narração ---')
    print('      ' + (narration_text[:400] + ('...' if len(narration_text) > 400 else '')).replace(chr(10), chr(10) + '      '))
    if npc_text:
        print('      --- reação NPC ---')
        print('      ' + npc_text.replace(chr(10), chr(10) + '      '))
"
}

# Turno 1: extrai informação do Grimwald (estabelece contexto).
run_action "2/4" "Sento no balcão e, com discrição, pergunto a Grimwald o que ele sabe sobre os bandidos da estrada do norte."

# Turno 2: o encontro emboscada — núcleo do PRD §5.
run_action "3/4" "Sigo pela estrada do norte até a clareira e tento armar uma emboscada contra Joren e os bandidos, aproximando-me pela borda da floresta com furtividade."

echo ""
echo "[4/4] Trace do turno 2 (pensamento do mestre)..."
curl -sf "$BASE_URL/campaigns/$CAMPAIGN_ID/turn/2/trace" | python3 -c "
import sys, json
data = json.load(sys.stdin)
trace = data['trace']
print('      player_action:', trace['player_action'][:80])
print('      robustness.ok:', trace['robustness']['ok'])
print('      retrieval rules:', len(trace.get('retrieval_rules', [])), 'lore:', len(trace.get('retrieval_lore', [])))
r = trace.get('ruling') or {}
print('      ruling.precisa_rolagem:', r.get('precisa_rolagem'), '| perícia:', r.get('pericia'), '| dificuldade:', r.get('dificuldade'))
print('      ruling.motivo_dificuldade:', (r.get('motivo_dificuldade') or '')[:120])
print('      ruling.npc_to_react:', r.get('npc_to_react'))
ro = trace.get('roll_outcome') or {}
if ro:
    print(f'      roll: {ro[\"roll\"][\"notation\"]} -> {ro[\"roll\"][\"total\"]} vs {ro[\"check\"][\"difficulty\"]} => success={ro[\"check\"][\"success\"]} margin={ro[\"check\"][\"margin\"]}')
print('      narration chars:', len(trace.get('narration') or ''))
print('      npc_reaction chars:', len(trace.get('npc_reaction') or ''))
print('      error:', trace.get('error'))
"

echo ""
echo "=== Critérios manuais ==="
echo "- Turno 2 deve ter: ruling estruturado, rolagem (Furtividade vs ~18), "
echo "  consequência aplicada, narração coerente com sucesso/falha, e reação do NPC."
echo "- Nenhum 'rejected' (ações foram válidas)."
echo "- Estado da campanha (GET /state) reflete o resultado do turno."
