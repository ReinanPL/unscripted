#!/usr/bin/env bash
# Smoke test do loop de turno — Fase 1
# Requer: curl, jq, backend rodando em http://localhost:8000

set -euo pipefail

BASE_URL="${BACKEND_URL:-http://localhost:8000}"
ACTION_TEXT="${1:-Olho em volta da taverna.}"

echo "==> Backend: $BASE_URL"

# 1. Health check
echo ""
echo "--- /health ---"
curl -sf "$BASE_URL/health" | jq .

# 2. Criar campanha
echo ""
echo "--- POST /campaigns ---"
CAMPAIGN_ID=$(curl -sf -X POST "$BASE_URL/campaigns" \
  -H "Content-Type: application/json" | jq -r '.campaign_id')
echo "campaign_id: $CAMPAIGN_ID"

# 3. Enviar ação e receber narração via SSE
echo ""
echo "--- POST /campaigns/$CAMPAIGN_ID/action ---"
echo "ação: \"$ACTION_TEXT\""
echo ""

curl -sN -X POST "$BASE_URL/campaigns/$CAMPAIGN_ID/action" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$ACTION_TEXT\"}" | while IFS= read -r line; do
    # Extrai somente linhas "data: {...}"
    if [[ "$line" == data:* ]]; then
        json="${line#data: }"
        type=$(echo "$json" | jq -r '.type')
        case "$type" in
            chunk)
                echo "$json" | jq -r '.text' | tr -d '\n'
                ;;
            done)
                echo ""
                echo ""
                echo "==> Narração completa."
                ;;
            error)
                echo ""
                echo "ERRO: $(echo "$json" | jq -r '.text')" >&2
                exit 1
                ;;
        esac
    fi
done
