#!/bin/bash

# Config
CONTAINERS="vllm-server gpt-researcher-cli"
OUTPUT_FILE="./outputs/gpu_stats.csv"
INTERVAL=0.1 # 1/10 second

# Header for the CSV file
echo "Timestamp,GPU_UUID,GPU_Name,GPU_Mem_Used_MiB,GPU_Util_Perc,GPU_Mem_Util_Perc" > "$OUTPUT_FILE"

echo "Starting GPU statistics collection (System-wide)..."
echo "Output file: $OUTPUT_FILE"
echo "Sampling interval: ${INTERVAL}s"
echo "Press [CTRL+C] to stop."

# Trap SIGINT (Ctrl+C) to exit gracefully
trap "echo -e '\nMonitoring stopped.'; exit" SIGINT

while true; do
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S.%3N")
    
    # Get overall GPU stats
    gpu_data=$(nvidia-smi --query-gpu=uuid,name,utilization.gpu,utilization.memory,memory.used --format=csv,noheader,nounits 2>/dev/null)
    
    if [ ! -z "$gpu_data" ]; then
        # Check if any of the target containers are running to trigger logging
        if docker ps --format '{{.Names}}' | grep -qE "^(vllm-server|gpt-researcher-cli)$"; then
            while IFS= read -r line; do
                GPU_UUID=$(echo "$line" | cut -d',' -f1 | xargs)
                GPU_NAME=$(echo "$line" | cut -d',' -f2 | xargs)
                GPU_UTIL=$(echo "$line" | cut -d',' -f3 | xargs)
                MEM_UTIL=$(echo "$line" | cut -d',' -f4 | xargs)
                MEM_USED=$(echo "$line" | cut -d',' -f5 | xargs)
                
                echo "$TIMESTAMP,$GPU_UUID,$GPU_NAME,$MEM_USED,$GPU_UTIL,$MEM_UTIL" >> "$OUTPUT_FILE"
            done <<< "$gpu_data"
        fi
    fi
    
    sleep "$INTERVAL"
done
