#!/bin/bash

# Start Ollama server in background
ollama serve &

# Wait for server to be ready (using ollama list command)
echo "Waiting for Ollama server to be ready..."
until ollama list > /dev/null 2>&1; do
    echo "Server not ready yet, waiting..."
    sleep 2
done
echo "Ollama server is ready!"

# Pull mistral model
ollama pull mistral

# Keep the server running
wait
