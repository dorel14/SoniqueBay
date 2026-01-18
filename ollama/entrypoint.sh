#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &
# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

echo "🔴 Retrieve models..."

ollama pull llama3.2:1b
echo "🟢 Done llama"
ollama pull qwen2.5:3b
echo "🟢 Done! Qwen2.5"
ollama pull exaone3.5:2.4b
echo "🟢 Done! EXAONE"
ollama pull gemma2:2b
echo "🟢 Done! gemma2"
ollama pull nomic-embed-text
echo "🟢 Done! nomic-embed-text"

# Wait for Ollama process to finish.
wait $pid