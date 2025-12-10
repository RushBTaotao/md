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

                pipe_begin = parse_time(0, pipe_begin_str)
                input_begin = parse_time(0, input_begin_str)
                pipe_end = input_begin  # pipe end = input begin
                input_end = parse_time(input_begin, input_end_str) if input_begin is not None else None
                output_begin = parse_time(input_end if input_end is not None else input_begin, output_begin_str) if input_begin is not None else None
                output_end = parse_time(output_begin, output_end_str) if output_begin is not None else None

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

    # Calculate maximum total duration for scaling long bars
    durations = []
    for task in tasks:
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
                plt.text(task['input_begin'] + scaled_input / 2, bar_y, f'{input_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')
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
                plt.text(task['output_begin'] + scaled_orange / 2, bar_y, f'{orange_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')

    # Set y-ticks and labels at bar centers
    plt.yticks([i + 0.3 for i in range(len(tasks))], [task['mode'] for task in reversed(tasks)])

    # Set labels and title from config
    plt.xlabel(config.get('x', 'Clock Cycles') if config else 'Clock Cycles')
    plt.ylabel(config.get('y', 'Modules/Tasks') if config else 'Modules/Tasks')
    plt.title(config.get('tile', 'Module Scheduling Gantt Chart') if config else 'Module Scheduling Gantt Chart')

    # Set x-axis range to original times
    max_time = max(task['output_end'] for task in tasks if task['output_end'] is not None)
    plt.xlim(0, max_time)

    # Set x-ticks at original positions, skip left side of length-1 blocks
    tick_positions = []
    tick_labels = []
    for task in tasks:
        input_duration = task['input_end'] - task['input_begin'] if task['input_end'] and task['input_begin'] else 0
        gray_duration = task['output_begin'] - task['input_end'] if task['output_begin'] and task['input_end'] else 0
        orange_duration = task['output_end'] - task['output_begin'] if task['output_end'] and task['output_begin'] else 0
        for orig_time in [task['pipe_begin'], task['input_begin'], task['input_end'], task['output_begin'], task['output_end']]:
            if orig_time is not None and orig_time not in tick_positions:
                # Skip left tick if it's the start of a length-1 block
                skip = False
                if orig_time == task['input_begin'] and input_duration == 1:
                    skip = True
                elif orig_time == task['input_end'] and gray_duration == 1:
                    skip = True
                elif orig_time == task['output_begin'] and orange_duration == 1:
                    skip = True
                if not skip:
                    tick_positions.append(orig_time)
                    tick_labels.append(str(orig_time))
    # Sort by position
    sorted_indices = sorted(range(len(tick_positions)), key=lambda i: tick_positions[i])
    plt.xticks([tick_positions[i] for i in sorted_indices], [tick_labels[i] for i in sorted_indices])

    # Show grid
    plt.grid(True, axis='x')

    # Add legend manually since broken_barh doesn't support labels directly
    gray_patch = plt.Rectangle((0,0),1,1,fc='gray')
    green_patch = plt.Rectangle((0,0),1,1,fc='green')
    orange_patch = plt.Rectangle((0,0),1,1,fc='orange')
    plt.legend([green_patch, gray_patch, orange_patch], ['Input', 'Transition', 'Output'], loc='upper right')

    # Add legend explaining scaling
    plt.text(0.02, 1.02, 'Non-uniform scaling applied', transform=plt.gca().transAxes, verticalalignment='bottom', fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.subplots_adjust(bottom=0.15)  # Leave space for button

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
