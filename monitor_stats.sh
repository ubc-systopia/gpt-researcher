#!/bin/bash

# Config
CONTAINERS="vllm-server gpt-researcher-cli"
OUTPUT_FILE="./outputs/docker_stats.csv"
INTERVAL=0.1 # 1/10 second

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running or you don't have permissions."
    exit 1
fi

# Header for the CSV file
echo "Timestamp,Container,CPU_Perc,Mem_Usage,Mem_Limit,Mem_Perc,Net_Input,Net_Output,Block_Input,Block_Output" > "$OUTPUT_FILE"

echo "Starting statistics collection for: $CONTAINERS"
echo "Output file: $OUTPUT_FILE"
echo "Sampling interval: ${INTERVAL}s"
echo "Press [CTRL+C] to stop."

# Trap SIGINT (Ctrl+C) to exit gracefully
trap "echo -e '\nMonitoring stopped.'; exit" SIGINT

while true; do
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S.%3N")
    
    # Format:
    # {{.Name}} - Container name
    # {{.CPUPerc}} - CPU percentage
    # {{.MemUsage}} - Memory usage / Limit
    # {{.MemPerc}} - Memory percentage
    # {{.NetIO}} - Network I/O (Sent / Received)
    # {{.BlockIO}} - Block I/O (Read / Write)
    
    stats=$(docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}}" $CONTAINERS)
    
    # Process each line from stats and add timestamp
    while IFS= read -r line; do
        if [ ! -z "$line" ]; then
            # Split MemUsage (e.g. "10MiB / 100MiB") into Usage and Limit
            # Split NetIO (e.g. "1kB / 2kB") into Input and Output
            # Split BlockIO (e.g. "1B / 2B") into Input and Output
            
            NAME=$(echo "$line" | cut -d',' -f1)
            CPU=$(echo "$line" | cut -d',' -f2)
            MEM_FULL=$(echo "$line" | cut -d',' -f3)
            MEM_PERC=$(echo "$line" | cut -d',' -f4)
            NET_FULL=$(echo "$line" | cut -d',' -f5)
            BLOCK_FULL=$(echo "$line" | cut -d',' -f6)
            
            MEM_USAGE=$(echo "$MEM_FULL" | awk -F' / ' '{print $1}')
            MEM_LIMIT=$(echo "$MEM_FULL" | awk -F' / ' '{print $2}')
            
            NET_IN=$(echo "$NET_FULL" | awk -F' / ' '{print $1}')
            NET_OUT=$(echo "$NET_FULL" | awk -F' / ' '{print $2}')
            
            BLOCK_IN=$(echo "$BLOCK_FULL" | awk -F' / ' '{print $1}')
            BLOCK_OUT=$(echo "$BLOCK_FULL" | awk -F' / ' '{print $2}')
            
            echo "$TIMESTAMP,$NAME,$CPU,$MEM_USAGE,$MEM_LIMIT,$MEM_PERC,$NET_IN,$NET_OUT,$BLOCK_IN,$BLOCK_OUT" >> "$OUTPUT_FILE"
        fi
    done <<< "$stats"
    
    sleep "$INTERVAL"
done
