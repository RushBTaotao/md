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
                input_begin = int(row['input begin'])
                input_end_str = row['input end']
                output_begin_str = row['output begin']
                output_end_str = row['output end']
                if input_end_str.startswith('a'):
                    input_end = input_begin + int(input_end_str[1:])
                else:
                    input_end = int(input_end_str)
                if output_begin_str.startswith('a'):
                    output_begin = input_end + int(output_begin_str[1:])
                else:
                    output_begin = int(output_begin_str)
                if output_end_str.startswith('a'):
                    output_end = output_begin + int(output_end_str[1:])
                else:
                    output_end = int(output_end_str)
                tasks.append({
                    'mode': row['mode'],
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

    # Draw each task with two parts: pipe (gray) and work (green) connected, with non-uniform scaling for positions and widths
    threshold = 50
    scale_short = 1.0
    scale_long = 0.1
    # Calculate scaled positions
    def scale_value(value):
        return value * scale_short if value <= threshold else threshold + (value - threshold) * scale_long

    for i, task in enumerate(reversed(tasks)):
        input_start = task['input_begin']
        input_duration = task['input_end'] - task['input_begin']
        gray_start = task['input_end']
        gray_duration = task['output_begin'] - task['input_end']
        orange_start = task['output_begin']
        orange_duration = task['output_end'] - task['output_begin']
        # Scale starts and durations
        scaled_input_start = scale_value(input_start)
        scaled_input = scale_value(input_duration)
        scaled_gray_start = scale_value(gray_start)
        scaled_gray = scale_value(gray_duration)
        scaled_orange_start = scale_value(orange_start)
        scaled_orange = scale_value(orange_duration)
        # Draw bars centered at i + 0.3
        bar_y = i + 0.3
        if scaled_input > 0:
            plt.barh(bar_y, scaled_input, left=scaled_input_start, height=0.6, color='green')
        if scaled_gray > 0:
            plt.barh(bar_y, scaled_gray, left=scaled_gray_start, height=0.6, color='gray')
        if scaled_orange > 0:
            plt.barh(bar_y, scaled_orange, left=scaled_orange_start, height=0.6, color='orange')
        # Add duration text centered on bars
        if input_duration > 0:
            plt.text(scaled_input_start + scaled_input / 2, bar_y, f'{input_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')
        if gray_duration > 0:
            plt.text(scaled_gray_start + scaled_gray / 2, bar_y, f'{gray_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')
        if orange_duration > 0:
            plt.text(scaled_orange_start + scaled_orange / 2, bar_y, f'{orange_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')

    # Set y-ticks and labels at bar centers
    plt.yticks([i + 0.3 for i in range(len(tasks))], [task['mode'] for task in reversed(tasks)])

    # Set labels and title from config
    plt.xlabel(config.get('x', 'Clock Cycles') if config else 'Clock Cycles')
    plt.ylabel(config.get('y', 'Modules/Tasks') if config else 'Modules/Tasks')
    plt.title(config.get('tile', 'Module Scheduling Gantt Chart') if config else 'Module Scheduling Gantt Chart')

    # Set x-axis range to scaled times
    max_scaled = max(scale_value(task['output_end']) for task in tasks)
    plt.xlim(0, max_scaled)

    # Set x-ticks at scaled positions with original labels
    tick_positions = []
    tick_labels = []
    for task in tasks:
        for orig_time in [task['input_begin'], task['input_end'], task['output_begin'], task['output_end']]:
            scaled_time = scale_value(orig_time)
            if scaled_time not in tick_positions:  # Avoid duplicates
                tick_positions.append(scaled_time)
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
