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

    # Load LangSmith stats to determine initialization and LLM inferences
    import glob
    import datetime
    langsmith_files = glob.glob('./outputs/*_langsmith_stats.csv')
    init_end_time_sec = None
    llm_intervals = []

    if langsmith_files:
        try:
            ls_df = pd.read_csv(langsmith_files[0])
            ls_df['Start Time'] = pd.to_datetime(ls_df['Start Time'])
            ls_df['End Time'] = pd.to_datetime(ls_df['End Time'])
            
            local_tz = datetime.datetime.now().astimezone().tzinfo
            ls_df['Start Time'] = ls_df['Start Time'].dt.tz_convert(local_tz).dt.tz_localize(None)
            ls_df['End Time'] = ls_df['End Time'].dt.tz_convert(local_tz).dt.tz_localize(None)
            
            # Filter to current run
            ls_df = ls_df[ls_df['Start Time'] >= start_time]
            
            if not ls_df.empty:
                init_end_time_sec = (ls_df['Start Time'].min() - start_time).total_seconds()
                
                # Extract LLM inference intervals
                llm_df = ls_df[ls_df['Run Type'] == 'llm']
                for _, row in llm_df.iterrows():
                    if pd.notna(row['End Time']):
                        start_sec = (row['Start Time'] - start_time).total_seconds()
                        end_sec = (row['End Time'] - start_time).total_seconds()
                        llm_intervals.append((start_sec, end_sec))
                
                # Merge overlapping intervals to prevent irregular shading
                if llm_intervals:
                    llm_intervals.sort(key=lambda x: x[0])
                    merged_intervals = [llm_intervals[0]]
                    for current in llm_intervals[1:]:
                        last = merged_intervals[-1]
                        if current[0] <= last[1]:
                            merged_intervals[-1] = (last[0], max(last[1], current[1]))
                        else:
                            merged_intervals.append(current)
                    llm_intervals = merged_intervals
        except Exception as e:
            print(f"Error processing langsmith stats: {e}")

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

    def add_overlays(ax, is_first=False):
        if init_end_time_sec is not None:
            label = 'LLM Initialization Completed' if is_first else '_nolegend_'
            ax.axvline(x=init_end_time_sec, color='red', linestyle='--', linewidth=1.5, label=label)
        
        added_llm_label = False
        for start_sec, end_sec in llm_intervals:
            label = '_nolegend_'
            if is_first and not added_llm_label:
                label = 'LLM Inference'
                added_llm_label = True
            ax.axvspan(start_sec, end_sec, color='orange', alpha=0.2, label=label)

    # CPU Utilization
    for container in docker_df['Container'].unique():
        data = docker_df[docker_df['Container'] == container]
        axes[0].plot(data['Elapsed_Time'], data['CPU_Perc_Val'], label=container)
    axes[0].set_ylabel('CPU Utilization (%)')
    axes[0].set_title('CPU Utilization vs Time')
    add_overlays(axes[0], is_first=True)
    axes[0].legend(loc='upper right')
    axes[0].grid(True, alpha=0.3)

    # System Memory Usage
    for container in docker_df['Container'].unique():
        data = docker_df[docker_df['Container'] == container]
        axes[1].plot(data['Elapsed_Time'], data['Mem_Usage_GiB'], label=container)
    axes[1].set_ylabel('Memory Usage (GiB)')
    axes[1].set_title('System Memory Usage vs Time')
    add_overlays(axes[1])
    axes[1].legend(loc='upper right')
    axes[1].grid(True, alpha=0.3)

    # GPU Utilization
    if not gpu_df.empty:
        axes[2].plot(gpu_df['Elapsed_Time'], gpu_df['GPU_Util_Perc'], label='Total GPU Utilization', color='orange')
    axes[2].set_ylabel('GPU Utilization (%)')
    axes[2].set_title('GPU Utilization vs Time')
    add_overlays(axes[2])
    axes[2].legend(loc='upper right')
    axes[2].grid(True, alpha=0.3)

    # GPU Memory Usage
    if not gpu_df.empty:
        axes[3].plot(gpu_df['Elapsed_Time'], gpu_df['GPU_Mem_Used_GiB'], label='Total GPU Memory Used', color='green')
    axes[3].set_ylabel('GPU Memory Used (GiB)')
    axes[3].set_title('GPU Memory Usage vs Time')
    add_overlays(axes[3])
    axes[3].legend(loc='upper right')
    axes[3].grid(True, alpha=0.3)

    # Network I/O
    for container in docker_df['Container'].unique():
        data = docker_df[docker_df['Container'] == container]
        axes[4].plot(data['Elapsed_Time'], data['Net_Input_GiB'], label=f"{container} In")
        axes[4].plot(data['Elapsed_Time'], data['Net_Output_GiB'], label=f"{container} Out", linestyle=':')
    axes[4].set_ylabel('Network I/O (GiB)')
    axes[4].set_title('Network I/O vs Time')
    add_overlays(axes[4])
    axes[4].legend(loc='upper right')
    axes[4].grid(True, alpha=0.3)

    # Block I/O
    for container in docker_df['Container'].unique():
        data = docker_df[docker_df['Container'] == container]
        axes[5].plot(data['Elapsed_Time'], data['Block_Input_GiB'], label=f"{container} Read")
        axes[5].plot(data['Elapsed_Time'], data['Block_Output_GiB'], label=f"{container} Write", linestyle=':')
    axes[5].set_ylabel('Block I/O (GiB)')
    axes[5].set_title('Block I/O vs Time')
    add_overlays(axes[5])
    axes[5].legend(loc='upper right')
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