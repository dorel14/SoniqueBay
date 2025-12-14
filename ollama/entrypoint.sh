#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &
# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

echo "🔴 Retrieve Phi3 mini model..."
ollama pull phi3:3.8b-mini-4k-instruct-q4_K_M
echo "🟢 Done!"

# Wait for Ollama process to finish.
wait $pid