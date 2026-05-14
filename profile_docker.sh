#!/bin/bash

# Configuration
MONITOR_STATS="./monitor_stats.sh"
MONITOR_GPU="./monitor_gpu.sh"
CLI_SERVICE="gpt-researcher-cli"

echo "Starting run..."

# Start monitoring in the background
if [ -f "$MONITOR_STATS" ]; then
    bash "$MONITOR_STATS" &
    STATS_PID=$!
    echo "Stats monitoring started (PID: $STATS_PID)"
fi

if [ -f "$MONITOR_GPU" ]; then
    bash "$MONITOR_GPU" &
    GPU_PID=$!
    echo "GPU monitoring started (PID: $GPU_PID)"
fi

# Run Docker Compose with automatic abort and cleanup
echo "Running Docker containers..."
docker compose up --abort-on-container-exit --exit-code-from "$CLI_SERVICE"

# Clean up Docker resources
echo "Cleaning up Docker containers and networks..."
docker compose down

# Stop monitoring
echo "Stopping monitors..."
[ ! -z "$STATS_PID" ] && kill $STATS_PID 2>/dev/null
[ ! -z "$GPU_PID" ] && kill $GPU_PID 2>/dev/null

# Generate plots
if [ -f "plot_resources.py" ]; then
    echo "Generating resource usage plots..."
    ./.venv/bin/python3 plot_resources.py
fi

echo "Task complete. Check ./outputs/ and ./logs/ for results."
