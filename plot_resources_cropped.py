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
                init_end_time_sec_orig = (ls_df['Start Time'].min() - start_time).total_seconds()
                
                # Rebase elapsed times so that 0 is the end of initialization
                docker_df['Elapsed_Time'] -= init_end_time_sec_orig
                gpu_df['Elapsed_Time'] -= init_end_time_sec_orig
                
                new_start_time = ls_df['Start Time'].min()
                init_end_time_sec = 0
                
                # Extract LLM inference intervals and compute concurrency
                events = []
                llm_df = ls_df[ls_df['Run Type'] == 'llm']
                for _, row in llm_df.iterrows():
                    if pd.notna(row['End Time']):
                        start_sec = (row['Start Time'] - new_start_time).total_seconds()
                        end_sec = (row['End Time'] - new_start_time).total_seconds()
                        events.append((start_sec, 'start'))
                        events.append((end_sec, 'end'))
                
                events.sort(key=lambda x: (x[0], 1 if x[1] == 'end' else 0))
                
                concurrent_calls = 0
                last_time = None
                for time, event_type in events:
                    if last_time is not None and time > last_time and concurrent_calls > 0:
                        llm_intervals.append((last_time, time, concurrent_calls))
                    
                    if event_type == 'start':
                        concurrent_calls += 1
                    else:
                        concurrent_calls -= 1
                    
                    last_time = time
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

    import matplotlib.cm as cm
    containers = docker_df['Container'].unique()
    num_entities = len(containers) + 4
    cmap = plt.get_cmap('tab20')
    colors = [cmap(i / max(1, num_entities - 1)) for i in range(num_entities)]
    
    init_line_color = colors[0]
    llm_bg_color = colors[-1]
    gpu_util_color = colors[-3]
    gpu_mem_color = colors[-2]
    
    container_colors = {c: colors[i+1] for i, c in enumerate(containers)}

    # Plotting
    fig, axes = plt.subplots(6, 1, figsize=(12, 26), sharex=True)
    plt.subplots_adjust(hspace=0.4)

    def add_overlays(ax, is_first=False):
        if init_end_time_sec is not None:
            label = 'LLM Initialization Completed' if is_first else '_nolegend_'
            ax.axvline(x=init_end_time_sec, color=init_line_color, linestyle='--', linewidth=1.5, label=label)
        
        added_llm_label = False
        for start_sec, end_sec, concurrency in llm_intervals:
            label = '_nolegend_'
            if is_first and not added_llm_label:
                label = 'LLM Inference (Darker = Higher Concurrency)'
                added_llm_label = True
            
            calc_alpha = min(0.1 + 0.15 * concurrency, 0.8)
            ax.axvspan(start_sec, end_sec, color=llm_bg_color, alpha=calc_alpha, label=label)

    # CPU Utilization
    for container in containers:
        data = docker_df[docker_df['Container'] == container]
        axes[0].plot(data['Elapsed_Time'], data['CPU_Perc_Val'], label=container, color=container_colors[container])
    axes[0].set_ylabel('CPU Utilization (%)')
    axes[0].set_title('CPU Utilization vs Time')
    add_overlays(axes[0], is_first=True)
    axes[0].legend(loc='upper right')
    axes[0].grid(True, alpha=0.3)

    # System Memory Usage
    for container in containers:
        data = docker_df[docker_df['Container'] == container]
        axes[1].plot(data['Elapsed_Time'], data['Mem_Usage_GiB'], label=container, color=container_colors[container])
    axes[1].set_ylabel('Memory Usage (GiB)')
    axes[1].set_title('System Memory Usage vs Time')
    add_overlays(axes[1])
    axes[1].legend(loc='upper right')
    axes[1].grid(True, alpha=0.3)

    # GPU Utilization
    if not gpu_df.empty:
        axes[2].plot(gpu_df['Elapsed_Time'], gpu_df['GPU_Util_Perc'], label='Total GPU Utilization', color=gpu_util_color)
    axes[2].set_ylabel('GPU Utilization (%)')
    axes[2].set_title('GPU Utilization vs Time')
    add_overlays(axes[2])
    axes[2].legend(loc='upper right')
    axes[2].grid(True, alpha=0.3)

    # GPU Memory Usage
    if not gpu_df.empty:
        axes[3].plot(gpu_df['Elapsed_Time'], gpu_df['GPU_Mem_Used_GiB'], label='Total GPU Memory Used', color=gpu_mem_color)
    axes[3].set_ylabel('GPU Memory Used (GiB)')
    axes[3].set_title('GPU Memory Usage vs Time')
    add_overlays(axes[3])
    axes[3].legend(loc='upper right')
    axes[3].grid(True, alpha=0.3)

    # Network I/O
    for container in containers:
        data = docker_df[docker_df['Container'] == container]
        axes[4].plot(data['Elapsed_Time'], data['Net_Input_GiB'], label=f"{container} In", color=container_colors[container])
        axes[4].plot(data['Elapsed_Time'], data['Net_Output_GiB'], label=f"{container} Out", linestyle=':', color=container_colors[container])
    axes[4].set_ylabel('Network I/O (GiB)')
    axes[4].set_title('Network I/O vs Time')
    add_overlays(axes[4])
    axes[4].legend(loc='upper right')
    axes[4].grid(True, alpha=0.3)

    # Block I/O
    for container in containers:
        data = docker_df[docker_df['Container'] == container]
        axes[5].plot(data['Elapsed_Time'], data['Block_Input_GiB'], label=f"{container} Read", color=container_colors[container])
        axes[5].plot(data['Elapsed_Time'], data['Block_Output_GiB'], label=f"{container} Write", linestyle=':', color=container_colors[container])
    axes[5].set_ylabel('Block I/O (GiB)')
    axes[5].set_title('Block I/O vs Time')
    add_overlays(axes[5])
    axes[5].legend(loc='upper right')
    axes[5].grid(True, alpha=0.3)

    # Add x-axis label to all subplots
    for ax in axes:
        ax.set_xlabel('Time (seconds)')
        ax.tick_params(labelbottom=True)
        if init_end_time_sec is not None:
            ax.set_xlim(left=init_end_time_sec)

    plt.tight_layout()
    output_file = './outputs/resource_timeline_cropped.png'
    plt.savefig(output_file, dpi=150)
    print(f"Plot saved to {output_file}")

if __name__ == "__main__":
    main()