import os
import csv
import matplotlib.pyplot as plt
import pandas as pd

def is_valid_data_line(parts):
    try:
        [float(part) for part in parts]
        return True
    except ValueError:
        return False

def extract_data_and_flutter(f06_filepath):
    with open(f06_filepath, 'r') as file:
        lines = file.readlines()

    data = []
    mode_data = {i: [] for i in range(1, 6)}

    for i in range(len(lines)):
        if "FLUTTER  SUMMARY" in lines[i]:
            mode = 1
            for j in range(i + 5, len(lines)):
                line = lines[j].strip()
                parts = line.split()
                if len(parts) >= 5 and is_valid_data_line(parts):
                    try:
                        kfreq = float(parts[0])
                        velocity = float(parts[2])
                        damping = float(parts[3])
                        frequency = float(parts[4])
                        if mode in mode_data and len(mode_data[mode]) < 121:
                            mode_data[mode].append([velocity, frequency, damping, kfreq])
                        if len(mode_data[mode]) == 121:
                            mode += 1
                            if mode > 5:
                                break
                    except (ValueError, IndexError) as e:
                        continue
                elif len(parts) > 0:
                    continue

    for mode in range(1, 6):
        for velocity, frequency, damping, kfreq in mode_data[mode]:
            data.append([mode, velocity, frequency, damping, kfreq])

    return data

def extract_mass(f06_filepath):
    with open(f06_filepath, 'r') as file:
        lines = file.readlines()

    for i in range(len(lines)):
        if "O U T P U T" in lines[i]:
            line = lines[i + 3].strip()
            if line.startswith('*'):
                parts = line.split()
                try:
                    mass = float(parts[1])
                    return mass
                except (ValueError, IndexError):
                    print(f"Failed to extract mass from line: {line} with parts: {parts}")
                    continue
    return None

f06_dir = 'generated_outputs'
data_csv_file = 'extracted_data.csv'
flutter_csv_file = 'flutter_speeds_and_mass.csv'

extracted_data = []
flutter_mass_data = []

for filename in os.listdir(f06_dir):
    if filename.endswith('.f06'):
        f06_filepath = os.path.join(f06_dir, filename)
        data = extract_data_and_flutter(f06_filepath)
        mass = extract_mass(f06_filepath)
        case_index = filename.split('_')[0]
        mach_number = filename.split('_')[1].replace('.f06', '').replace('m', 'M')

        for mode, velocity, frequency, damping, kfreq in data:
            extracted_data.append([f"{case_index}_{mach_number}", f"Mode {mode}", velocity, damping, frequency, kfreq])

        flutter_mass_data.append([f"{case_index}_{mach_number}", None, mass, None])

extracted_data.sort(key=lambda x: (int(x[0].split('_')[0]), float(x[0].split('_')[1].replace('M', ''))))
flutter_mass_data.sort(key=lambda x: (int(x[0].split('_')[0]), float(x[0].split('_')[1].replace('M', ''))))

with open(data_csv_file, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Index', 'Mode', 'Velocity', 'Damping', 'Frequency', 'Kfreq'])
    writer.writerows(extracted_data)

with open(flutter_csv_file, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Index', 'Flutter Speed', 'Mass', 'Flutter Frequency'])
    writer.writerows(flutter_mass_data)

print(f"Data has been saved to '{data_csv_file}'")
print(f"Flutter speeds and mass values have been saved to '{flutter_csv_file}'")

def interpolate_flutter_point(v1, d1, v2, d2, f1, f2):
    if d1 >= 0 or d2 <= 0:  # Ensure the change is from negative to positive
        return None, None
    flutter_speed = v1 - d1 * (v2 - v1) / (d2 - d1)
    flutter_frequency = f1 + (f2 - f1) * (flutter_speed - v1) / (v2 - v1)
    return flutter_speed, flutter_frequency

def find_flutter_speed_from_csv(data_csv_file, flutter_csv_file):
    df_data = pd.read_csv(data_csv_file)
    flutter_speeds = []

    for index, group in df_data.groupby('Index'):
        min_flutter_speed = None
        min_flutter_frequency = None
        for mode in group['Mode'].unique():
            mode_data = group[group['Mode'] == mode]
            mode_data = mode_data.sort_values(by='Velocity')

            for i in range(1, len(mode_data)):
                v1 = mode_data.iloc[i-1]['Velocity']
                d1 = mode_data.iloc[i-1]['Damping']
                v2 = mode_data.iloc[i]['Velocity']
                d2 = mode_data.iloc[i]['Damping']
                f1 = mode_data.iloc[i-1]['Frequency']
                f2 = mode_data.iloc[i]['Frequency']
                kfreq2 = mode_data.iloc[i]['Kfreq']

                if kfreq2 == 0:
                    continue

                flutter_speed, flutter_frequency = interpolate_flutter_point(v1, d1, v2, d2, f1, f2)
                if flutter_speed is not None:
                    if min_flutter_speed is None or flutter_speed < min_flutter_speed:
                        min_flutter_speed = flutter_speed
                        min_flutter_frequency = flutter_frequency
                        print(f"Interpolated flutter speed for {index}, mode {mode}: {flutter_speed}, frequency: {flutter_frequency}")
                    break
        if min_flutter_speed is not None:
            flutter_speeds.append((index, min_flutter_speed, min_flutter_frequency))

    df_flutter = pd.read_csv(flutter_csv_file)
    flutter_speed_dict = dict([(i[0], (i[1], i[2])) for i in flutter_speeds])
    df_flutter['Flutter Speed'] = df_flutter['Index'].map(lambda x: flutter_speed_dict[x][0] if x in flutter_speed_dict else None)
    df_flutter['Flutter Frequency'] = df_flutter['Index'].map(lambda x: flutter_speed_dict[x][1] if x in flutter_speed_dict else None)
    df_flutter.to_csv(flutter_csv_file, index=False)

    print(f"Updated flutter speeds and frequencies have been saved to '{flutter_csv_file}'")

find_flutter_speed_from_csv(data_csv_file, flutter_csv_file)

def plot_graphs(extracted_data, flutter_csv_file):
    flutter_data = pd.read_csv(flutter_csv_file)

    for index, flutter_speed, mass, flutter_frequency in flutter_data.itertuples(index=False):
        data = [row for row in extracted_data if row[0] == index]
        if not data:
            continue

        modes = sorted(set(row[1] for row in data))

        plt.figure(figsize=(10, 12))

        plt.subplot(2, 1, 1)
        for mode in modes:
            mode_data = [row for row in data if row[1] == mode]
            velocities = [row[2] for row in mode_data]
            dampings = [row[3] for row in mode_data]
            plt.plot(velocities, dampings, label=mode)
        if flutter_speed:
            plt.axvline(x=flutter_speed, color='r', linestyle='--', label='Flutter Speed')
            plt.text(flutter_speed + 5, 0.1, f'Flutter Speed = {flutter_speed:.2f}', color='black', fontsize=12, fontweight='bold', verticalalignment='bottom', horizontalalignment='left', bbox=dict(facecolor='white', alpha=0.5))
        plt.axhline(y=0, color='black', linestyle='--', label='Zero Damping')
        plt.xlabel('Velocity')
        plt.ylabel('Damping')
        plt.ylim(-1, 1)
        plt.title('Velocity vs. Damping')
        plt.legend()
        plt.grid(True)

        plt.subplot(2, 1, 2)
        for mode in modes:
            mode_data = [row for row in data if row[1] == mode]
            frequencies = [row[4] for row in mode_data]
            velocities = [row[2] for row in mode_data]
            plt.plot(velocities, frequencies, label=mode)
        if flutter_speed and flutter_frequency:
            plt.axvline(x=flutter_speed, color='r', linestyle='--', label='Flutter Speed')
            plt.axhline(y=flutter_frequency, color='g', linestyle='--', label='Flutter Frequency')
            plt.text(flutter_speed + 5, flutter_frequency + 1, f'Flutter Frequency = {flutter_frequency:.2f}', color='black', fontsize=12, fontweight='bold', verticalalignment='bottom', horizontalalignment='left', bbox=dict(facecolor='white', alpha=0.5))
            # Ensure valid axis limits
            if pd.notna(flutter_speed) and pd.notna(flutter_frequency):
                plt.xlim(flutter_speed - 20, flutter_speed + 20)
                plt.ylim(flutter_frequency - 10, flutter_frequency + 10)
        plt.xlabel('Velocity')
        plt.ylabel('Frequency')
        plt.title('Frequency vs. Velocity')
        plt.legend()
        plt.grid(True)

        plt.tight_layout()
        graph_dir = 'graphs'
        os.makedirs(graph_dir, exist_ok=True)
        plt.savefig(os.path.join(graph_dir, f'{index}.png'))
        plt.close()

plot_graphs(extracted_data, flutter_csv_file)