import matplotlib.pyplot as plt
import matplotlib.widgets as widgets
import numpy as np
import csv

csv_file = 'tasks.csv'
exit_flag = False
config = {}

def read_tasks():
    tasks = []
    config = {}
    try:
        with open(csv_file, 'r', newline='', encoding='utf-8') as file:
            lines = file.readlines()
            # Read config from first 3 lines
            for i in range(3):
                parts = lines[i].strip().split(',')
                if len(parts) >= 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    config[key] = value
            # Read tasks from remaining lines
            reader = csv.DictReader(lines[3:])
            for row in reader:
                mode = row['mode'].strip()
                pipe_begin_str = row['pipe begin'].strip()
                input_begin_str = row['input begin'].strip()
                input_end_str = row['input end'].strip()
                output_begin_str = row['output begin'].strip()
                output_end_str = row['output end'].strip()

                # Parse times, handle empty and 'a'
                def parse_time(base, time_str):
                    if not time_str:
                        return None
                    if time_str.startswith('a'):
                        return base + int(time_str[1:])
                    else:
                        return int(time_str)

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
        print(f"Error: CSV file '{csv_file}' not found.")
        return [], {}
    except (KeyError, ValueError, IndexError) as e:
        print(f"Error reading CSV: {e}")
        return [], {}
    return tasks, config

def plot_gantt(tasks, config=None):
    if not tasks:
        print("No tasks to plot.")
        return

    # Filter PMF tasks
    pmf_tasks = [task for task in tasks if task['mode'].startswith('PMF_')]

    # Calculate maximum total duration for scaling long bars
    durations = []
    for task in tasks:
        if task['output_end'] is not None and task['input_begin'] is not None:
            total_duration = task['output_end'] - task['input_begin']
            if total_duration > 0:
                durations.append(total_duration)
    if not durations:
        print("No valid durations.")
        return

    if not plt.fignum_exists(1):
        plt.figure(1, figsize=(12, 8))  # Larger figure size
    else:
        plt.figure(1)
    plt.clf()  # Clear the figure

    # Draw each task with non-uniform scaling for bar widths only (positions use original)
    threshold = 50
    scale_long = 0.1

    def scale_duration(duration):
        return duration if duration <= threshold else threshold + (duration - threshold) * scale_long

    # Y positions for PMF summaries
    pmf_input_y = len(tasks) + 0.3
    pmf_output_y = len(tasks) + 1.3

    # Colors for PMF segments using 4 saturation levels, cycling
    green_colors = ['#90EE90', '#32CD32', '#228B22', '#006400']  # lightgreen, limegreen, forestgreen, darkgreen
    orange_colors = ['#FFA500', '#FF8C00', '#FF6347', '#DC143C']  # orange, darkorange, tomato, crimson

    # Draw PMF_INPUT summary
    for i, task in enumerate(pmf_tasks):
        suffix = task['mode'].split('_', 1)[1] if '_' in task['mode'] else task['mode']
        input_begin = task['input_begin']
        input_end = task['input_end']
        if input_begin is not None and input_end is not None:
            input_duration = input_end - input_begin
            if input_duration > 0:
                scaled_input = scale_duration(input_duration)
                color = green_colors[i % 4]
                plt.barh(pmf_input_y, scaled_input, left=input_begin, height=0.6, color=color)
                plt.text(input_begin + scaled_input / 2, pmf_input_y, suffix, ha='center', va='center', fontsize=8, color='white', weight='bold')

    # Draw PMF_OUTPUT summary
    for i, task in enumerate(pmf_tasks):
        suffix = task['mode'].split('_', 1)[1] if '_' in task['mode'] else task['mode']
        output_begin = task['output_begin']
        output_end = task['output_end']
        if output_begin is not None and output_end is not None:
            output_duration = output_end - output_begin
            if output_duration > 0:
                scaled_output = scale_duration(output_duration)
                color = orange_colors[i % 4]
                plt.barh(pmf_output_y, scaled_output, left=output_begin, height=0.6, color=color)
                plt.text(output_begin + scaled_output / 2, pmf_output_y, suffix, ha='center', va='center', fontsize=8, color='white', weight='bold')

    for i, task in enumerate(reversed(tasks)):
        bar_y = i + 0.3
        # Pipe segment (gray)
        if task['pipe_begin'] is not None and task['pipe_end'] is not None:
            pipe_duration = task['pipe_end'] - task['pipe_begin']
            scaled_pipe = scale_duration(pipe_duration)
            if scaled_pipe > 0:
                plt.barh(bar_y, scaled_pipe, left=task['pipe_begin'], height=0.6, color='gray')
                plt.text(task['pipe_begin'] + scaled_pipe / 2, bar_y, f'{pipe_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')
        # Input segment (green)
        if task['input_begin'] is not None and task['input_end'] is not None:
            input_duration = task['input_end'] - task['input_begin']
            scaled_input = scale_duration(input_duration)
            if scaled_input > 0:
                plt.barh(bar_y, scaled_input, left=task['input_begin'], height=0.6, color='green')
                # Adjust text position if overlapping with output
                text_x = task['input_begin'] + scaled_input / 2
                if task['output_begin'] is not None and task['output_end'] is not None and task['input_end'] > task['output_begin']:
                    # Overlapping, place text at the left part of input segment
                    overlap_start = task['output_begin']
                    input_center = task['input_begin'] + scaled_input / 2
                    if input_center >= overlap_start:
                        text_x = task['input_begin'] + (overlap_start - task['input_begin']) / 2
                plt.text(text_x, bar_y, f'{input_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')
        # Transition (gray)
        if task['input_end'] is not None and task['output_begin'] is not None:
            gray_duration = task['output_begin'] - task['input_end']
            scaled_gray = scale_duration(gray_duration)
            if scaled_gray > 0:
                plt.barh(bar_y, scaled_gray, left=task['input_end'], height=0.6, color='gray')
                plt.text(task['input_end'] + scaled_gray / 2, bar_y, f'{gray_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')
        # Output segment (orange)
        if task['output_begin'] is not None and task['output_end'] is not None:
            orange_duration = task['output_end'] - task['output_begin']
            scaled_orange = scale_duration(orange_duration)
            if scaled_orange > 0:
                plt.barh(bar_y, scaled_orange, left=task['output_begin'], height=0.6, color='orange')
                # Adjust text position if overlapping with input
                text_x = task['output_begin'] + scaled_orange / 2
                if task['input_begin'] is not None and task['input_end'] is not None and task['output_begin'] < task['input_end']:
                    # Overlapping, place text at the right part of output segment
                    overlap_end = task['input_end']
                    output_center = task['output_begin'] + scaled_orange / 2
                    if output_center <= overlap_end:
                        text_x = overlap_end + (task['output_end'] - overlap_end) / 2
                plt.text(text_x, bar_y, f'{orange_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')

    # Add y labels next to the bars
    # For PMF summaries
    pmf_input_left = min(task['input_begin'] for task in pmf_tasks if task['input_begin'] is not None) if pmf_tasks else 0
    pmf_output_left = min(task['output_begin'] for task in pmf_tasks if task['output_begin'] is not None) if pmf_tasks else 0
    plt.text(pmf_input_left - 5, pmf_input_y, 'PMF_INPUT', ha='right', va='center', fontsize=10)
    plt.text(pmf_output_left - 5, pmf_output_y, 'PMF_OUTPUT', ha='right', va='center', fontsize=10)

    # For individual tasks
    for i, task in enumerate(reversed(tasks)):
        bar_y = i + 0.3
        left_times = [t for t in [task['pipe_begin'], task['input_begin'], task['input_end'], task['output_begin'], task['output_end']] if t is not None]
        if left_times:
            left_most = min(left_times)
            plt.text(left_most - 5, bar_y, task['mode'], ha='right', va='center', fontsize=10)

    # Remove y ticks
    plt.yticks([])

    # Set labels and title from config
    plt.xlabel(config.get('x', 'Clock Cycles') if config else 'Clock Cycles')
    plt.ylabel(config.get('y', 'Modules/Tasks') if config else 'Modules/Tasks')
    plt.title(config.get('tile', 'Module Scheduling Gantt Chart') if config else 'Module Scheduling Gantt Chart')

    # Set x-axis range to original times
    max_time = max(task['output_end'] for task in tasks if task['output_end'] is not None)
    plt.xlim(0, max_time)

    # Set x-ticks at the leftmost of each task's valid segments
    tick_positions = set()
    for task in tasks:
        times = [t for t in [task['pipe_begin'], task['input_begin'], task['input_end'], task['output_begin'], task['output_end']] if t is not None]
        if times:
            tick_positions.add(min(times))
    tick_positions = sorted(list(tick_positions))
    plt.xticks(tick_positions, [str(t) for t in tick_positions], rotation=45, ha='right')

    # Show grid
    plt.grid(True, axis='x')

    # Add legend manually since broken_barh doesn't support labels directly
    gray_patch = plt.Rectangle((0,0),1,1,fc='gray')
    green_patch = plt.Rectangle((0,0),1,1,fc='green')
    orange_patch = plt.Rectangle((0,0),1,1,fc='orange')
    plt.legend([green_patch, gray_patch, orange_patch], ['Input', 'Transition', 'Output'], loc='upper right', bbox_to_anchor=(1.05, 1.1))

    # Add legend explaining scaling
    plt.text(0.02, 1.02, 'Non-uniform scaling applied', transform=plt.gca().transAxes, verticalalignment='bottom', fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.subplots_adjust(bottom=0.15, left=0.2)  # Leave space for button and y labels

    # Add refresh button
    ax_button = plt.axes([0.81, 0.02, 0.1, 0.05])  # [left, bottom, width, height]
    button = widgets.Button(ax_button, 'Refresh')
    button.on_clicked(lambda event: refresh_chart())

    plt.savefig('gantt_chart.png', dpi=150, bbox_inches='tight')
    plt.draw()  # Ensure the button is drawn
    plt.pause(0.01)  # Small pause to allow drawing
    plt.show()

def refresh_chart():
    global tasks, config
    tasks, config = read_tasks()
    if tasks:
        plot_gantt(tasks, config)
        print("Chart refreshed.")

# Read and plot initial data
tasks, config = read_tasks()
if tasks:
    plot_gantt(tasks, config)
    print("Gantt chart saved as gantt_chart.png")
else:
    print("No tasks found in CSV.")
