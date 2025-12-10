import matplotlib.pyplot as plt
import numpy as np
import csv

# Read task data from CSV file
csv_file = 'tasks.csv'
tasks = []
try:
    with open(csv_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            pipe_begin = int(row['pipe begin'])
            work_begin_str = row['work begin']
            work_end_str = row['work end']
            if work_begin_str.startswith('a'):
                work_begin = pipe_begin + int(work_begin_str[1:])
            else:
                work_begin = int(work_begin_str)
            if work_end_str.startswith('a'):
                work_end = work_begin + int(work_end_str[1:])
            else:
                work_end = int(work_end_str)
            tasks.append({
                'mode': row['mode'],
                'pipe_begin': pipe_begin,
                'work_begin': work_begin,
                'work_end': work_end
            })
except FileNotFoundError:
    print(f"Error: CSV file '{csv_file}' not found.")
    exit()
except KeyError as e:
    print(f"Error: Missing column in CSV: {e}")
    exit()
except ValueError as e:
    print(f"Error: Invalid data in CSV: {e}")
    exit()

# Handle edge cases: check if task list is empty
if not tasks:
    print("Error: Task list is empty. Please add tasks to the CSV file.")
    exit()

# Calculate maximum total duration for scaling long bars
durations = []
for task in tasks:
    total_duration = task['work_end'] - task['pipe_begin']
    if total_duration > 0:
        durations.append(total_duration)
if not durations:
    print("Error: All tasks have invalid durations. Please check CSV data.")
    exit()

max_duration = max(durations)
scale_factor = 50 / max_duration if max_duration > 0 else 1  # Avoid division by zero

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))

# Draw each task with two parts: pipe (gray) and work (green) connected
for i, task in enumerate(reversed(tasks)):
    pipe_start = task['pipe_begin']
    pipe_duration = task['work_begin'] - task['pipe_begin']
    work_duration = task['work_end'] - task['work_begin']
    # Use broken_barh to connect the parts
    bar_data = []
    if pipe_duration > 0:
        bar_data.append((pipe_start, pipe_duration))
    if work_duration > 0:
        bar_data.append((task['work_begin'], work_duration))
    if bar_data:
        ax.broken_barh(bar_data, (i, 0.6), facecolors=['gray', 'green'])
        # Add duration text for pipe and work
        if pipe_duration > 0:
            ax.text(pipe_start + pipe_duration / 2, i + 0.3, f'{pipe_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')
        if work_duration > 0:
            ax.text(task['work_begin'] + work_duration / 2, i + 0.3, f'{work_duration}', ha='center', va='center', fontsize=8, color='white', weight='bold')

# Set y-ticks and labels, centering labels on the bars
ax.set_yticks([i + 0.3 for i in range(len(tasks))])
ax.set_yticklabels([task['mode'] for task in reversed(tasks)])

# Set labels and title
ax.set_xlabel('Clock Cycles (Original)')
ax.set_ylabel('Modules/Tasks')
ax.set_title('Module Scheduling Gantt Chart (Clock Cycles)')

# Set x-axis range
total_time = max(task['work_end'] for task in tasks)
ax.set_xlim(0, total_time)

# Set x-ticks at bar start and end points
all_times = set()
for task in tasks:
    all_times.add(task['pipe_begin'])
    all_times.add(task['work_begin'])
    all_times.add(task['work_end'])
ax.set_xticks(sorted(all_times))

# Show grid
ax.grid(True, axis='x')

# Add legend manually since broken_barh doesn't support labels directly
gray_patch = plt.Rectangle((0,0),1,1,fc='gray')
green_patch = plt.Rectangle((0,0),1,1,fc='green')
ax.legend([gray_patch, green_patch], ['Pipe', 'Work'], loc='upper right')

# Add legend explaining scaling
ax.text(0.02, 0.98, f'Bars scaled by {scale_factor:.2f}x', transform=ax.transAxes, verticalalignment='top', fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Display figure
plt.tight_layout()
plt.savefig('gantt_chart.png', dpi=150, bbox_inches='tight')  # Save as image file
print("Gantt chart saved as gantt_chart.png")
plt.show()  # Display figure if in GUI-supporting environment
