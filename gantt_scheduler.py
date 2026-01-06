import matplotlib.pyplot as plt
import matplotlib.widgets as widgets
import numpy as np
import csv
import argparse
import os

def read_tasks(csv_file_path):
    tasks = []
    config = {}
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as file:
            lines = file.readlines()
            # Read config from first 3 lines
            for i in range(min(3, len(lines))):
                parts = lines[i].strip().split(',')
                if len(parts) >= 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    config[key] = value
            # Read tasks from remaining lines
            if len(lines) > 3:
                reader = csv.DictReader(lines[3:])
                for row in reader:
                    mode = row['mode'].replace(' ', '')
                    pipe_begin_str = row['pipe begin'].strip()
                    input_begin_str = row['input begin'].strip()
                    input_end_str = row['input end'].strip()
                    output_begin_str = row['output begin'].strip()
                    output_end_str = row['output end'].strip()

                    # Parse times, handle empty and 'a'
                    def parse_time(base, time_str):
                        if not time_str:
                            return None
                        time_str = time_str.strip().rstrip(',')
                        if time_str.startswith('a'):
                            return base + int(time_str[1:])
                        else:
                            try:
                                return int(time_str)
                            except ValueError:
                                return None

                    pipe_begin = parse_time(0, pipe_begin_str) if pipe_begin_str else None
                    input_begin = parse_time(0, input_begin_str) if input_begin_str else None
                    pipe_end = input_begin  # pipe end = input begin
                    input_end = parse_time(input_begin, input_end_str) if input_begin is not None else (parse_time(0, input_end_str) if input_end_str else None)
                    output_begin = parse_time(input_end if input_end is not None else input_begin, output_begin_str) if input_begin is not None or input_end is not None or input_end_str else (parse_time(0, output_begin_str) if output_begin_str else None)
                    output_end = parse_time(output_begin, output_end_str) if output_begin is not None else (parse_time(0, output_end_str) if output_end_str else None)

                    tasks.append({
                        'mode': mode,
                        'pipe_begin': pipe_begin,
                        'pipe_end': pipe_end,
                        'input_begin': input_begin,
                        'input_end': input_end,
                        'output_begin': output_begin,
                        'output_end': output_end
                    })
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file_path}' not found.")
        return [], {}
    except (KeyError, ValueError, IndexError) as e:
        print(f"Error reading CSV: {e}")
        return [], {}
    return tasks, config

def plot_gantt(tasks, config=None, output=None, save_only=False):
    if not tasks:
        print("No tasks to plot.")
        return

    # Check for overlaps between different modes' input or output segments
    def check_overlap(start1, end1, start2, end2):
        return max(start1, start2) < min(end1, end2)

    overlaps = []
    for i in range(len(tasks)):
        for j in range(i+1, len(tasks)):
            task1 = tasks[i]
            task2 = tasks[j]
            if task1['mode'] != task2['mode'] and task1['mode'].startswith('PMF_') and task2['mode'].startswith('PMF_'):
                # Check input overlap
                if (task1['input_begin'] is not None and task1['input_end'] is not None and
                    task2['input_begin'] is not None and task2['input_end'] is not None):
                    if check_overlap(task1['input_begin'], task1['input_end'], task2['input_begin'], task2['input_end']):
                        msg = f"Warning: Input segment overlap between mode '{task1['mode']}' and '{task2['mode']}' at coordinates {max(task1['input_begin'], task2['input_begin'])} to {min(task1['input_end'], task2['input_end'])}"
                        print(msg)
                        overlaps.append(msg)

    # Filter PMF tasks
    pmf_tasks = [task for task in tasks if task['mode'].startswith('PMF_')]

    # Calculate maximum total duration for scaling long bars
    durations = []
    max_output_end = 0
    for task in tasks:
        if task['output_end'] is not None:
            max_output_end = max(max_output_end, task['output_end'])
        if task['output_end'] is not None and task['input_begin'] is not None:
            total_duration = task['output_end'] - task['input_begin']
            if total_duration > 0:
                durations.append(total_duration)
    
    # We strictly use plt.figure(figsize=...) as per original logic
    if len(tasks) > 40:
        fig = plt.figure(figsize=(38, 10))  # Larger size for >40 tasks
    else:
        fig = plt.figure(figsize=(19, 10))  # Smaller size for <=40 tasks
    plt.clf()  # Clear the figure

    # Y positions for PMF summaries
    pmf_input_y = len(tasks) + 0.3
    pmf_output_y = len(tasks) + 1.3

    # Colors for PMF input summary segments based on mode size and type
    def get_pmf_input_color(mode):
        if 'M8' in mode:
            return '#90EE90'  # lightgreen for M8
        elif 'F8' in mode:
            return '#32CD32'  # limegreen for F8
        elif 'M16' in mode:
            return '#FFA500'  # orange for M16
        elif 'F16' in mode:
            return '#FF8C00'  # darkorange for F16
        elif 'M32' in mode:
            return '#FFD700'  # gold for M32
        elif 'F32' in mode:
            return '#FF6347'  # tomato for F32
        else:
            return '#228B22'  # default forestgreen

    # Colors for PMF output summary segments based on mode size and type
    def get_pmf_output_color(mode):
        if 'M8' in mode:
            return '#FF6347'  # tomato for M8
        elif 'F8' in mode:
            return '#DC143C'  # crimson for F8
        elif 'M16' in mode:
            return '#FF8C00'  # darkorange for M16
        elif 'F16' in mode:
            return '#FFA500'  # orange for F16
        elif 'M32' in mode:
            return '#FFD700'  # gold for M32
        elif 'F32' in mode:
            return '#FF4500'  # orangered for F32
        else:
            return '#B22222'  # firebrick default

    # Draw PMF_INPUT summary
    for i, task in enumerate(pmf_tasks):
        suffix = task['mode'].split('_', 1)[1] if '_' in task['mode'] else task['mode']
        input_begin = task['input_begin']
        input_end = task['input_end']
        if input_begin is not None and input_end is not None:
            input_duration = input_end - input_begin
            if input_duration > 0:
                color = get_pmf_input_color(task['mode'])
                plt.barh(pmf_input_y, input_duration, left=input_begin, height=0.6, color=color)
                plt.text(input_begin + input_duration / 2, pmf_input_y, suffix, ha='center', va='center', fontsize=7, color='white', weight='bold')

    # Draw PMF_OUTPUT summary
    for i, task in enumerate(pmf_tasks):
        suffix = task['mode'].split('_', 1)[1] if '_' in task['mode'] else task['mode']
        output_begin = task['output_begin']
        output_end = task['output_end']
        if output_begin is not None and output_end is not None:
            output_duration = output_end - output_begin
            if output_duration > 0:
                color = get_pmf_output_color(task['mode'])
                plt.barh(pmf_output_y, output_duration, left=output_begin, height=0.6, color=color)
                plt.text(output_begin + output_duration / 2, pmf_output_y, suffix, ha='center', va='center', fontsize=7, color='white', weight='bold')

    for i, task in enumerate(reversed(tasks)):
        bar_y = i + 0.3
        # Pipe segment (gray)
        if task['pipe_begin'] is not None and task['pipe_end'] is not None:
            pipe_duration = task['pipe_end'] - task['pipe_begin']
            if pipe_duration > 0:
                plt.barh(bar_y, pipe_duration, left=task['pipe_begin'], height=0.6, color='gray')
        # Input segment with color based on mode
        if task['input_begin'] is not None and task['input_end'] is not None:
            input_duration = task['input_end'] - task['input_begin']
            if input_duration > 0:
                color = 'green'
                plt.barh(bar_y, input_duration, left=task['input_begin'], height=0.6, color=color)
                # Adjust text position if overlapping with output
                text_x = task['input_begin'] + input_duration / 2
                if task['output_begin'] is not None and task['output_end'] is not None and task['input_end'] > task['output_begin']:
                    # Overlapping, place text at the left part of input segment
                    overlap_start = task['output_begin']
                    input_center = task['input_begin'] + input_duration / 2
                    if input_center >= overlap_start:
                        text_x = task['input_begin'] + (overlap_start - task['input_begin']) / 2
                plt.text(text_x, bar_y, f'{input_duration}', ha='center', va='center', fontsize=7, color='white', weight='bold')
        # Transition (gray)
        if task['input_end'] is not None and task['output_begin'] is not None:
            gray_duration = task['output_begin'] - task['input_end']
            if gray_duration > 0:
                plt.barh(bar_y, gray_duration, left=task['input_end'], height=0.6, color='gray')
                plt.text(task['input_end'] + gray_duration / 2, bar_y, f'{gray_duration}', ha='center', va='center', fontsize=7, color='white', weight='bold')
        # Output segment (orange)
        if task['output_begin'] is not None and task['output_end'] is not None:
            orange_duration = task['output_end'] - task['output_begin']
            if orange_duration > 0:
                plt.barh(bar_y, orange_duration, left=task['output_begin'], height=0.6, color='orange')
                # Adjust text position if overlapping with input
                text_x = task['output_begin'] + orange_duration / 2
                if task['input_begin'] is not None and task['input_end'] is not None and task['output_begin'] < task['input_end']:
                    # Overlapping, place text at the right part of output segment
                    overlap_end = task['input_end']
                    output_center = task['output_begin'] + orange_duration / 2
                    if output_center <= overlap_end:
                        text_x = overlap_end + (task['output_end'] - overlap_end) / 2
                plt.text(text_x, bar_y, f'{orange_duration}', ha='center', va='center', fontsize=7, color='white', weight='bold')

    # Add y labels next to the bars
    # For PMF summaries
    pmf_input_left = min(task['input_begin'] for task in pmf_tasks if task['input_begin'] is not None) if pmf_tasks else 0
    pmf_output_left = min(task['output_begin'] for task in pmf_tasks if task['output_begin'] is not None) if pmf_tasks else 0
    plt.text(pmf_input_left - 2, pmf_input_y, 'PMF_INPUT', ha='right', va='center', fontsize=7)
    plt.text(pmf_output_left - 2, pmf_output_y, 'PMF_OUTPUT', ha='right', va='center', fontsize=7)

    # For individual tasks
    for i, task in enumerate(reversed(tasks)):
        bar_y = i + 0.3
        left_times = [t for t in [task['pipe_begin'], task['input_begin'], task['input_end'], task['output_begin'], task['output_end']] if t is not None]
        if left_times:
            left_most = min(left_times)
            plt.text(left_most - 1, bar_y, task['mode'], ha='right', va='center', fontsize=7)

    # Remove y ticks
    plt.yticks([])
    plt.ylim(-0.5, len(tasks) + 2.5)

    # Set labels and title from config
    plt.xlabel(config.get('x', 'Clock Cycles') if config else 'Clock Cycles')
    plt.ylabel(config.get('y', 'Modules/Tasks') if config else 'Modules/Tasks')
    plt.title(config.get('tile', 'Module Scheduling Gantt Chart') if config else 'Module Scheduling Gantt Chart')

    # Set x-ticks at the leftmost of each task's valid segments
    tick_positions = set()
    for task in tasks:
        times = [t for t in [task['pipe_begin'], task['input_begin'], task['input_end'], task['output_begin'], task['output_end']] if t is not None]
        if times:
            tick_positions.add(min(times))
    tick_positions = sorted(list(tick_positions))
    # Add max_time to tick positions for rightmost marker
    max_time = max((task['output_end'] for task in tasks if task['output_end'] is not None), default=0)
    tick_positions.append(max_time)
    plt.xticks(tick_positions, [str(t) for t in tick_positions], rotation=45, ha='right')

    # Set x-axis range to original times
    min_time = min(tick_positions) if tick_positions else 0
    plt.xlim(min_time - 2, max_time)

    # Show grid
    plt.grid(True, axis='x')

    # Add legend manually
    gray_patch = plt.Rectangle((0,0),1,1,fc='gray')
    green_patch = plt.Rectangle((0,0),1,1,fc='green')
    orange_patch = plt.Rectangle((0,0),1,1,fc='orange')
    plt.legend([green_patch, gray_patch, orange_patch], ['Input', 'Transition', 'Output'], loc='upper right', bbox_to_anchor=(1.05, 1.05))

    # Add overlap warnings to the bottom left corner
    if overlaps:
        warning_text = "\n".join(overlaps)
        plt.figtext(0.01, 0.01, warning_text, fontsize=8, color='red', ha='left', va='bottom', bbox=dict(facecolor='white', alpha=0.8))

    plt.subplots_adjust(bottom=0.2 if overlaps else 0.15, left=0.05, right=0.95)

    if not config:
        config = {}
    
    output_file = output if output else config.get('tile', 'Module Scheduling Gantt Chart').replace(' ', '_') + '.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    
    if not save_only:
        # Add refresh button (interactive mode only)
        ax_button = plt.axes([0.81, 0.02, 0.1, 0.05])
        button = widgets.Button(ax_button, 'Refresh')
        # Note: self-refresh logic requires the function to know its source, 
        # but for library use, it's simpler to keep it basic or skip in non-interactive.
        plt.draw()
        plt.pause(0.01)
        plt.show()
    else:
        plt.close(fig)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv-file', default='tasks.csv', help='Input CSV file')
    parser.add_argument('--output', help='Output PNG file name')
    parser.add_argument('--save-only', action='store_true', help='Save PNG without displaying')

    args = parser.parse_args()
    csv_file_path = args.csv_file

    tasks, config = read_tasks(csv_file_path)
    if tasks:
        plot_gantt(tasks, config, args.output, args.save_only)
    else:
        print("No tasks found in CSV.")

if __name__ == "__main__":
    main()
