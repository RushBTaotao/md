"""
处理包含PMF数据的Excel文件并生成甘特图和汇总图。

此脚本读取Excel文件('mrg.xlsx')，提取以'PMF'开头的sheet，
保存为CSV，使用gantt_scheduler.py生成单个甘特PNG，
收集PMF任务，清理和处理它们，并生成按size和round分组的汇总图。
"""

import openpyxl
import csv
import subprocess
import sys
import os
import matplotlib.pyplot as plt
from collections import defaultdict
import re

def read_tasks_from_csv(csv_file_path):
    """
    从CSV文件中读取任务和配置。

    解析CSV文件，从前3行提取配置，其余行读取任务。
    处理带有'a'符号的时间解析。

    参数:
        csv_file_path (str): CSV文件路径。

    返回:
        tuple: (任务列表, 配置字典)
    """
    tasks = []
    config = {}
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as file:
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
        print(f"Error: CSV file '{csv_file_path}' not found.")
        return [], {}
    except (KeyError, ValueError, IndexError) as e:
        print(f"Error reading CSV: {e}")
        return [], {}
    return tasks, config

def get_round(sheet):
    """
    从sheet名称确定round。

    'round0' -> '0', 'round0-3'或其他 -> '1'。

    参数:
        sheet (str): Sheet名称。

    返回:
        str: '0' 或 '1'。
    """
    if 'round0' in sheet and 'round0-3' not in sheet:
        return '0'
    else:
        return '1'

def get_c(sheet):
    """
    从sheet名称确定c。

    'c0' -> 'c0', 'c1' -> 'c1', 其他 -> 'other'。

    参数:
        sheet (str): Sheet名称。

    返回:
        str: 'c0', 'c1', 或 'other'。
    """
    if 'c0' in sheet:
        return 'c0'
    elif 'c1' in sheet:
        return 'c1'
    else:
        return 'other'

def collect_pmf_tasks(csv_files, sheet_names):
    """
    从CSV文件中收集并增强PMF任务。

    对每个CSV，读取任务，过滤PMF，添加sheet元数据(uv, c, round)，
    并为round0-3 sheet复制。

    参数:
        csv_files (list): CSV文件路径列表。
        sheet_names (list): 对应的sheet名称。

    返回:
        list: 增强的任务，mode已标记。
    """
    all_tasks = []
    for csv_file, sheet in zip(csv_files, sheet_names):
        tasks, _ = read_tasks_from_csv(csv_file)
        uv = 'UV' if 'UV' in sheet else 'Y'
        c_str = get_c(sheet)
        rounds = []
        if 'round0-3' in sheet:
            rounds = ['0', '1']
        else:
            rounds = [get_round(sheet)]
        pmf_tasks = [t for t in tasks if t['mode'].startswith('PMF_')]
        for t in pmf_tasks:
            for round_str in rounds:
                task = {**t, 'sheet': sheet, 'round': round_str, 'c': c_str, 'uv': uv, 'original_mode': t['mode']}
                task['mode'] = f"{t['mode']}_{uv}_{c_str}_{round_str}"
                all_tasks.append(task)
    return all_tasks

def clean_pmf_tasks(tasks):
    """
    清理和调整PMF任务。

    根据uv和size条件，去除_a/_b mode，调整_c mode的输出时间，保留相关字段。

    参数:
        tasks (list): 原始任务列表。

    返回:
        list: 清理的任务，时间已调整。
    """
    cleaned = []
    for task in tasks:
        mode = task['mode']
        size = get_size(mode)
        uv = task['uv']

        # 1. Remove _a/_b for specific conditions
        remove = False
        if uv == 'Y' and size in ['16', '32', '64'] and ('_a' in task.get('original_mode', mode) or '_b' in task.get('original_mode', mode)):
            remove = True
        if uv == 'UV' and size in ['8', '16', '32'] and ('_a' in task.get('original_mode', mode) or '_b' in task.get('original_mode', mode)):
            remove = True
        if remove:
            continue

        # 2. Adjust _c for specific conditions
        adjust = False
        if uv == 'Y' and size in ['16', '32', '64'] and '_c' in task.get('original_mode', mode):
            adjust = True
        if uv == 'UV' and size in ['8', '16', '32'] and '_c' in task.get('original_mode', mode):
            adjust = True
        if adjust:
            old_ob = task['output_begin']
            old_oe = task['output_end']
            if old_ob is not None and old_oe is not None:
                new_ob = old_oe + 2
                new_oe = old_oe - old_ob + new_ob
                task['output_begin'] = new_ob
                task['output_end'] = new_oe

        # Only keep output_begin, output_end, mode, sheet, round, c, uv
        cleaned.append({
            'mode': mode,
            'output_begin': task['output_begin'],
            'output_end': task['output_end'],
            'sheet': task['sheet'],
            'round': task['round'],
            'c': task['c'],
            'uv': task['uv']
        })
    return cleaned

def get_size(mode):
    match = re.search(r'[MF](\d+)', mode)
    if match:
        return match.group(1)
    else:
        return 'other'

def merge_intervals(intervals):
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for current in intervals[1:]:
        last = merged[-1]
        if current[0] <= last[1]:
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            merged.append(current)
    return merged

def find_overlaps(intervals):
    if not intervals:
        return []
    overlaps = []
    for i in range(len(intervals)):
        for j in range(i+1, len(intervals)):
            start1, end1 = intervals[i]
            start2, end2 = intervals[j]
            overlap_start = max(start1, start2)
            overlap_end = min(end1, end2)
            if overlap_start < overlap_end:
                overlaps.append((overlap_start, overlap_end))
    return overlaps

def plot_summary(tasks, pmf_sheets):
    # Group by size, uv, round (combine c0/c1)
    grouped = defaultdict(list)
    for task in tasks:
        size = get_size(task['mode'])
        uv = task['uv']
        round = task['round']
        grouped[(size, uv, round)].append(task)

    # For each round
    sizes_small = ['4', '8']
    sizes_large = ['16', '32']
    for r in ['0', '1']:
        grouped_small = {k: v for k, v in grouped.items() if k[0] in sizes_small and k[2] == r}
        if grouped_small:
            plot_single_summary(grouped_small, f'PMF_Summary_4_8_round{r}.png', f'PMF Output Summary 4/8 Round {r}', xlim=(0,200))

        grouped_large = {k: v for k, v in grouped.items() if k[0] in sizes_large and k[2] == r}
        if grouped_large:
            plot_single_summary(grouped_large, f'PMF_Summary_16_32_round{r}.png', f'PMF Output Summary 16/32 Round {r}', xlim=(0,800))

def collect_summary_data(tasks, sizes, r, xlim):
    filtered = [task for task in tasks if get_size(task['mode']) in sizes and task['round'] == r]
    if xlim:
        filtered = [task for task in filtered if task['output_begin'] is not None and task['output_end'] is not None and task['output_begin'] >= xlim[0] and task['output_end'] <= xlim[1]]
    return filtered

def generate_summary_plot(tasks, sizes, r, xlim):
    filtered = collect_summary_data(tasks, sizes, r, xlim)
    grouped = defaultdict(list)
    for task in filtered:
        size = get_size(task['mode'])
        uv = task['uv']
        grouped[(size, uv)].append(task)
    if grouped:
        size_str = '_'.join(sizes)
        plot_single_summary(grouped, f'PMF_Summary_{size_str}_round{r}.png', f'PMF Output Summary {"/".join(sizes)} Round {r}', xlim)

def plot_single_summary(grouped, filename, title, xlim=None):
    plt.figure(figsize=(19, 10))
    plt.clf()

    y_pos = 0
    labels = []
    all_times = []
    for (size, uv), task_list in grouped.items():
        # Filter tasks within xlim if xlim is set
        if xlim:
            task_list = [task for task in task_list if task['output_begin'] is not None and task['output_end'] is not None and task['output_begin'] >= xlim[0] and task['output_end'] <= xlim[1]]
        if not task_list:
            continue  # Skip if no tasks
        labels.append(f'{size} {uv}')
        for task in task_list:
            ob = task['output_begin']
            oe = task['output_end']
            if ob is not None and oe is not None:
                duration = oe - ob
                if duration > 0:
                    color = 'moccasin' if uv == 'Y' else 'lightgreen'
                    plt.barh(y_pos, duration, left=ob, height=0.4, color=color)
                    # Text with Y/UV/c0/c1/mode
                    mode_parts = task['mode'].split('_')
                    if len(mode_parts) > 6:  # has _a/_b/_c
                        mode_short = '_'.join(mode_parts[1:4])
                    else:
                        mode_short = '_'.join(mode_parts[1:3])
                    suffix = f"{task['uv']} {task['c']} {mode_short}"
                    plt.text(ob + duration / 2, y_pos, suffix, ha='center', va='center', fontsize=7, color='black', weight='bold', rotation=45)
                all_times.extend([ob, oe])
        # Draw red overlaps
        overlaps = find_overlaps([(task['output_begin'], task['output_end']) for task in task_list if task['output_begin'] is not None and task['output_end'] is not None])
        if overlaps:
            broken_overlaps = [(s, e - s) for s, e in overlaps]
            plt.broken_barh(broken_overlaps, (y_pos, 0.4), facecolors='red')
        y_pos += 1

    # Add summary bar with overlaps in red
    all_tasks_in_group = [task for task_list in grouped.values() for task in task_list]
    if all_tasks_in_group:
        # Draw all task bars in gray
        for task in all_tasks_in_group:
            ob = task['output_begin']
            oe = task['output_end']
            if ob is not None and oe is not None:
                duration = oe - ob
                if duration > 0:
                    plt.barh(y_pos, duration, left=ob, height=0.4, color='gray')
        # Draw red overlaps
        overlaps = find_overlaps([(task['output_begin'], task['output_end']) for task in all_tasks_in_group if task['output_begin'] is not None and task['output_end'] is not None])
        if overlaps:
            broken_overlaps = [(s, e - s) for s, e in overlaps]
            plt.broken_barh(broken_overlaps, (y_pos, 0.4), facecolors='red')
        # Text
        all_times_sum = [t for task in all_tasks_in_group for t in [task['output_begin'], task['output_end']] if t is not None]
        if all_times_sum:
            total_start = min(all_times_sum)
            total_end = max(all_times_sum)
            plt.text((total_start + total_end) / 2, y_pos, 'Summary', ha='center', va='center', fontsize=7, color='black', weight='bold')
        labels.append('Summary')
        y_pos += 1

    # Set y ticks with labels
    plt.yticks(range(len(labels)), labels)

    plt.xlabel('Clock Cycles')
    plt.ylabel('Size / Type / C')
    plt.title(title)

    # Set x range
    if xlim:
        plt.xlim(xlim)
    else:
        if all_times:
            min_t = min(all_times)
            max_t = max(all_times)
            plt.xlim(min_t, max_t)

    # Set x ticks at output_begin positions
    tick_positions = sorted(set([task['output_begin'] for task in all_tasks_in_group if task['output_begin'] is not None]))
    plt.xticks(tick_positions, [str(t) for t in tick_positions], rotation=45, ha='right')

    plt.grid(True, axis='x')
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def main():
    excel_file = 'mrg.xlsx'
    if not os.path.exists(excel_file):
        print(f"Error: Excel file '{excel_file}' not found.")
        sys.exit(1)

    # Load workbook with data_only to get calculated values
    wb = openpyxl.load_workbook(excel_file, data_only=True)
    pmf_sheets = [sheet for sheet in wb.sheetnames if sheet.startswith('PMF')]

    if not pmf_sheets:
        print("No PMF_ sheets found in the Excel file.")
        sys.exit(0)

    print(f"Found PMF sheets: {pmf_sheets}")

    for sheet_name in pmf_sheets:
        # Read sheet
        sheet = wb[sheet_name]
        # Save to CSV
        csv_file = f"{sheet_name}.csv"
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for row in sheet.iter_rows(values_only=True):
                    writer.writerow(row)
            print(f"Saved {sheet_name} to {csv_file}")
        except PermissionError:
            print(f"Warning: Cannot write to {csv_file}, file may be open. Skipping.")
            continue

        # Generate PNG
        png_file = f"{sheet_name}.png"
        cmd = [sys.executable, 'gantt_scheduler.py', '--csv-file', csv_file, '--output', png_file, '--save-only']
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error generating PNG for {sheet_name}: {result.stderr}")
        else:
            print(f"Generated {png_file}")

    # Now collect all PMF tasks
    csv_files = [f"{sheet}.csv" for sheet in pmf_sheets]
    all_pmf_tasks = collect_pmf_tasks(csv_files, pmf_sheets)
    print(f"Collected {len(all_pmf_tasks)} PMF tasks from all sheets.")

    # Clean tasks
    cleaned_tasks = clean_pmf_tasks(all_pmf_tasks)
    print(f"After cleaning: {len(cleaned_tasks)} tasks.")

    # Plot summary
    sizes = ['4', '8', '16', '32']
    for size in sizes:
        for r in ['0', '1']:
            xlim = (0, 200) if size in ['4', '8'] else (0, 800)
            generate_summary_plot(cleaned_tasks, [size], r, xlim)
    print("Generated 8 summary PNGs: PMF_Summary_4_round0.png, PMF_Summary_4_round1.png, PMF_Summary_8_round0.png, PMF_Summary_8_round1.png, PMF_Summary_16_round0.png, PMF_Summary_16_round1.png, PMF_Summary_32_round0.png, PMF_Summary_32_round1.png")

if __name__ == "__main__":
    main()
