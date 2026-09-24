#!/usr/bin/env bash
set -e

MODEL_NAME="${1:-qwen2.5:7b}"

echo "============================================================"
echo "Pulling LLM Model '${MODEL_NAME}' for Intelligent Concierge"
echo "============================================================"

if command -v ollama >/dev/null 2>&1; then
    echo " Detected native Ollama on host (GPU mode). Pulling model locally..."
    ollama pull "${MODEL_NAME}"
elif command -v docker >/dev/null 2>&1 && docker ps | grep -q "hotel-ollama"; then
    echo " Detected running container 'hotel-ollama'. Pulling model inside container..."
    docker exec -it hotel-ollama ollama pull "${MODEL_NAME}"
else
    echo "❌ Neither native ollama command nor running hotel-ollama container found."
    echo "Please install native Ollama (brew install ollama) or start Docker."
    exit 1
fi

echo " Model '${MODEL_NAME}' is ready for inference!"
