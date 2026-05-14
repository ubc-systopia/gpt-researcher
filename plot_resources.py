import pandas as pd
import matplotlib.pyplot as plt
import re
import sys

def parse_units(value):
    """Converts strings like '302.7MiB', '100.36%', '1.2GiB' to float."""
    if pd.isna(value) or value == 'N/A' or value == '':
        return 0.0
    
    # Remove percentage sign
    value = str(value).replace('%', '').strip()
    
    # Check for memory units
    match = re.match(r"([0-9\.]+)\s*([a-zA-Z]*)", value)
    if not match:
        try:
            return float(value)
        except:
            return 0.0
            
    num, unit = match.groups()
    num = float(num)
    unit = unit.lower()
    
    if 'g' in unit:
        return num * 1024
    if 'k' in unit:
        return num / 1024
    if 'b' in unit and 'm' not in unit:
        return num / (1024 * 1024)
    
    return num # Default is MiB

def main():
    print("Loading data...")
    try:
        docker_df = pd.read_csv('./outputs/docker_stats.csv')
        gpu_df = pd.read_csv('./outputs/gpu_stats.csv')
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return

    # Convert timestamps
    docker_df['Timestamp'] = pd.to_datetime(docker_df['Timestamp'])
    gpu_df['Timestamp'] = pd.to_datetime(gpu_df['Timestamp'])

    # Calculate elapsed time in seconds
    start_time = min(docker_df['Timestamp'].min(), gpu_df['Timestamp'].min())
    docker_df['Elapsed_Time'] = (docker_df['Timestamp'] - start_time).dt.total_seconds()
    gpu_df['Elapsed_Time'] = (gpu_df['Timestamp'] - start_time).dt.total_seconds()

    # Clean Docker and GPU data
    docker_df['CPU_Perc_Val'] = docker_df['CPU_Perc'].apply(parse_units)
    docker_df['Mem_Usage_GiB'] = docker_df['Mem_Usage'].apply(parse_units) / 1024
    docker_df['Net_Input_GiB'] = docker_df['Net_Input'].apply(parse_units) / 1024
    docker_df['Net_Output_GiB'] = docker_df['Net_Output'].apply(parse_units) / 1024
    docker_df['Block_Input_GiB'] = docker_df['Block_Input'].apply(parse_units) / 1024
    docker_df['Block_Output_GiB'] = docker_df['Block_Output'].apply(parse_units) / 1024

    gpu_df['GPU_Mem_Used_GiB'] = pd.to_numeric(gpu_df['GPU_Mem_Used_MiB'], errors='coerce').fillna(0) / 1024
    gpu_df['GPU_Util_Perc'] = pd.to_numeric(gpu_df['GPU_Util_Perc'], errors='coerce').fillna(0)

    # Plotting
    fig, axes = plt.subplots(6, 1, figsize=(12, 26), sharex=True)
    plt.subplots_adjust(hspace=0.4)

    # CPU Utilization
    for container in docker_df['Container'].unique():
        data = docker_df[docker_df['Container'] == container]
        axes[0].plot(data['Elapsed_Time'], data['CPU_Perc_Val'], label=container, marker='.')
    axes[0].set_ylabel('CPU Utilization (%)')
    axes[0].set_title('CPU Utilization vs Time')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # System Memory Usage
    for container in docker_df['Container'].unique():
        data = docker_df[docker_df['Container'] == container]
        axes[1].plot(data['Elapsed_Time'], data['Mem_Usage_GiB'], label=container, marker='.')
    axes[1].set_ylabel('Memory Usage (GiB)')
    axes[1].set_title('System Memory Usage vs Time')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # GPU Utilization
    if not gpu_df.empty:
        axes[2].plot(gpu_df['Elapsed_Time'], gpu_df['GPU_Util_Perc'], label='Total GPU Utilization', color='orange', marker='.', linestyle='--')
    axes[2].set_ylabel('GPU Utilization (%)')
    axes[2].set_title('GPU Utilization vs Time')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    # GPU Memory Usage
    if not gpu_df.empty:
        axes[3].plot(gpu_df['Elapsed_Time'], gpu_df['GPU_Mem_Used_GiB'], label='Total GPU Memory Used', color='green', marker='.', linestyle='--')
    axes[3].set_ylabel('GPU Memory Used (GiB)')
    axes[3].set_title('GPU Memory Usage vs Time')
    axes[3].legend()
    axes[3].grid(True, alpha=0.3)

    # Network I/O
    for container in docker_df['Container'].unique():
        data = docker_df[docker_df['Container'] == container]
        axes[4].plot(data['Elapsed_Time'], data['Net_Input_GiB'], label=f"{container} In", marker='.')
        axes[4].plot(data['Elapsed_Time'], data['Net_Output_GiB'], label=f"{container} Out", marker='x', linestyle=':')
    axes[4].set_ylabel('Network I/O (GiB)')
    axes[4].set_title('Network I/O vs Time')
    axes[4].legend()
    axes[4].grid(True, alpha=0.3)

    # Block I/O
    for container in docker_df['Container'].unique():
        data = docker_df[docker_df['Container'] == container]
        axes[5].plot(data['Elapsed_Time'], data['Block_Input_GiB'], label=f"{container} Read", marker='.')
        axes[5].plot(data['Elapsed_Time'], data['Block_Output_GiB'], label=f"{container} Write", marker='x', linestyle=':')
    axes[5].set_ylabel('Block I/O (GiB)')
    axes[5].set_title('Block I/O vs Time')
    axes[5].legend()
    axes[5].grid(True, alpha=0.3)

    # Add x-axis label to all subplots
    for ax in axes:
        ax.set_xlabel('Time (seconds)')
        ax.tick_params(labelbottom=True)

    plt.tight_layout()
    output_file = './outputs/resource_timeline.png'
    plt.savefig(output_file, dpi=150)
    print(f"Plot saved to {output_file}")

if __name__ == "__main__":
    main()