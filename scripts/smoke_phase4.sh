#!/usr/bin/env bash
# smoke_phase4.sh — valida que o NarratorAgent usa o lore do capítulo 1 via RAG.
# Pré-requisitos:
#   docker compose up -d (backend + postgres rodando, ingestão executada no startup)
#   conteúdo do capítulo 1 em content/chapters/chapter-01/chapter.yaml
set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "=== Smoke test Fase 4: RAG + grounding em lore ==="
echo ""

# 1. Confirma ingestão no banco
echo "[1/4] Contagem de chunks no banco..."
docker compose exec -T postgres psql -U unscripted -d unscripted -t -c \
    "SELECT corpus, COUNT(*) FROM rag_chunks GROUP BY corpus ORDER BY corpus;" \
    | sed 's/^ */      /'

# 2. Cria campanha e captura ID
echo ""
echo "[2/4] Criando campanha (Paladino)..."
RESPONSE=$(curl -sf -X POST "$BASE_URL/campaigns" \
    -H "Content-Type: application/json" \
    -d '{"character": "paladino"}')
CAMPAIGN_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['campaign_id'])")
echo "      campaign_id: $CAMPAIGN_ID"

run_action() {
    local label="$1"
    local action="$2"
    echo ""
    echo "[$label] Ação: \"$action\""
    curl -sN -X POST "$BASE_URL/campaigns/$CAMPAIGN_ID/action" \
        -H "Content-Type: application/json" \
        -d "{\"text\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$action")}" \
        --max-time 90 | python3 -c "
import sys, json
chunks = []
for line in sys.stdin:
    line = line.strip()
    if line.startswith('data:'):
        evt = json.loads(line[5:].strip())
        if evt['type'] == 'chunk':
            chunks.append(evt['text'])
        elif evt['type'] == 'done':
            break
narration = ''.join(chunks).strip()
print(f'      ({len(narration)} chars)')
print('      ' + narration.replace('\n', '\n      '))
"
}

# 3. Ação com grounding no capítulo 1
run_action "3/4" "Pergunto ao Grimwald o que ele sabe sobre Joren Lâmina de Junho."

# 4. Ação sem grounding (esperado: narração genérica, sem inventar fatos)
run_action "4/4" "Saio da taverna e olho para o céu."

echo ""
echo "=== Critérios manuais ==="
echo "- A narração de [3/4] deve mencionar Grimwald ou Joren de forma coerente"
echo "  com o conteúdo do capítulo 1 (ex.aspectos: ex-guarda, taverna, vila)."
echo "- A narração de [4/4] não deve inventar fatos específicos do mundo."
