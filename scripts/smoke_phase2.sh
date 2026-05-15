#!/usr/bin/env bash
# smoke_phase2.sh — Valida persistência de campanhas
# Pré-requisito: docker compose up -d (backend + postgres rodando)
set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "=== Smoke test Fase 2: Persistência ==="
echo ""

# 1. Criar campanha com Paladino
echo "[1/6] Criando campanha (Paladino)..."
RESPONSE=$(curl -sf -X POST "$BASE_URL/campaigns" \
  -H "Content-Type: application/json" \
  -d '{"character": "paladino"}')
CAMPAIGN_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['campaign_id'])")
echo "      campaign_id: $CAMPAIGN_ID"

# 2. Verificar estado inicial (sem hidden_state)
echo ""
echo "[2/6] Verificando estado inicial..."
STATE=$(curl -sf "$BASE_URL/campaigns/$CAMPAIGN_ID/state")
echo "$STATE" | python3 -c "
import sys, json
s = json.load(sys.stdin)
char = s['character']
print(f\"      Personagem: {char['name']} (classe: {char['character_class']})\")
print(f\"      HP: {char['hp_current']}/{char['hp_max']}\")
assert 'hidden_state' not in s, 'FALHA: hidden_state exposto!'
print('      hidden_state: ausente (correto)')
"

# 3. Verificar que Guerreiro teria ficha distinta
echo ""
echo "[3/6] Criando campanha (Guerreiro) para verificar fichas distintas..."
RESPONSE_G=$(curl -sf -X POST "$BASE_URL/campaigns" \
  -H "Content-Type: application/json" \
  -d '{"character": "guerreiro"}')
CAMPAIGN_ID_G=$(echo "$RESPONSE_G" | python3 -c "import sys,json; print(json.load(sys.stdin)['campaign_id'])")
STATE_G=$(curl -sf "$BASE_URL/campaigns/$CAMPAIGN_ID_G/state")
echo "$STATE_G" | python3 -c "
import sys, json
s = json.load(sys.stdin)
char = s['character']
print(f\"      Personagem: {char['name']} (classe: {char['character_class']})\")
print(f\"      HP: {char['hp_current']}/{char['hp_max']}\")
"

# 4. Fazer um turno no Paladino
echo ""
echo "[4/6] Enviando ação ao Paladino (SSE)..."
echo "      (aguarda narração via streaming...)"
curl -sN -X POST "$BASE_URL/campaigns/$CAMPAIGN_ID/action" \
  -H "Content-Type: application/json" \
  -d '{"text": "Olho ao redor e descrevo o que vejo."}' \
  --max-time 90 | python3 -c "
import sys
chunks = []
for line in sys.stdin:
    line = line.strip()
    if line.startswith('data:'):
        import json
        evt = json.loads(line[5:].strip())
        if evt['type'] == 'chunk':
            chunks.append(evt['text'])
        elif evt['type'] == 'done':
            break
narration = ''.join(chunks)
print(f'      Narração recebida ({len(narration)} chars)')
print(f'      Preview: {narration[:120]}...' if len(narration) > 120 else f'      Narração: {narration}')
"

# 5. Verificar log (deve ter 1 entrada)
echo ""
echo "[5/6] Verificando log da partida..."
LOG=$(curl -sf "$BASE_URL/campaigns/$CAMPAIGN_ID/log")
echo "$LOG" | python3 -c "
import sys, json
log = json.load(sys.stdin)
entries = log['history']
print(f'      Entradas no histórico: {len(entries)}')
if entries:
    e = entries[0]
    print(f\"      Turno {e['turn']}: ação='{e['player_action'][:50]}'\")
"

# 6. Instrução de persistência
echo ""
echo "[6/6] Testando persistência..."
echo "      Para validar persistência completa, execute:"
echo ""
echo "        docker compose restart backend"
echo ""
echo "      Depois rode:"
echo ""
echo "        curl $BASE_URL/campaigns/$CAMPAIGN_ID/state"
echo "        curl $BASE_URL/campaigns/$CAMPAIGN_ID/log"
echo ""
echo "      O estado e o histórico devem estar intactos."
echo ""
echo "=== Smoke test concluído ==="
