import os
import csv
import matplotlib.pyplot as plt
import pandas as pd
import re

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
            # skip the next 5 lines (header), then read data rows
            for j in range(i + 5, len(lines)):
                line = lines[j].strip()
                parts = line.split()
                if len(parts) >= 5 and is_valid_data_line(parts):
                    try:
                        kfreq    = float(parts[0])
                        velocity = float(parts[2])
                        damping  = float(parts[3])
                        frequency= float(parts[4])
                        # Only collect up to 121 rows per mode
                        if mode in mode_data and len(mode_data[mode]) < 121:
                            mode_data[mode].append([velocity, frequency, damping, kfreq])
                        if len(mode_data[mode]) == 121:
                            mode += 1
                            if mode > 5:
                                break
                    except (ValueError, IndexError):
                        continue
                elif len(parts) > 0:
                    # If we hit a non‐numeric or partial row, just keep scanning
                    continue

    # Flatten out mode_data into one big `data` list
    for mode in range(1, 6):
        for velocity, frequency, damping, kfreq in mode_data[mode]:
            data.append([mode, velocity, frequency, damping, kfreq])

    return data

def extract_mass(f06_filepath):
    with open(f06_filepath, 'r') as file:
        lines = file.readlines()

    for i in range(len(lines)):
        if "O U T P U T" in lines[i]:
            # The mass value is on the third line after "O U T P U T"
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

# ───────────────────────────────────────────────────────────────
# 1) Now we simply look for ALL files ending in .f06
# 2) We take the filename (e.g. "optimal_solution80.f06") → root = "optimal_solution80"
# 3) We use a regex to pull out the trailing digits (80, 85, etc.) as the Mach number.
# 4) If there are no trailing digits, mach_number will be None.
# ──────────────────────────────────────────────────────────────

f06_dir           = 'generated_outputs'
data_csv_file     = 'extracted_data.csv'
flutter_csv_file  = 'flutter_speeds_and_mass.csv'

extracted_data    = []
flutter_mass_data = []

for filename in os.listdir(f06_dir):
    if not filename.lower().endswith('.f06'):
        continue

    f06_filepath = os.path.join(f06_dir, filename)

    # (A) Extract the "root" (everything before .f06), e.g. "optimal_solution80"
    root_name = os.path.splitext(filename)[0]  # -> "optimal_solution80"

    # (B) Use regex to grab the trailing digits as Mach.  If no trailing digits, leave as None.
    m = re.search(r"(\d+)$", root_name)
    mach_number = m.group(1) if m else None
    # If you want to convert to a float, you can do: float(mach_number) if m else None

    # (C) Now collect data + mass
    data = extract_data_and_flutter(f06_filepath)
    mass = extract_mass(f06_filepath)

    # (D) For every row in `data`, append [index, mode, velocity, damping, frequency, kfreq]
    for mode, velocity, frequency, damping, kfreq in data:
        extracted_data.append([
            root_name, 
            f"Mode {mode}", 
            velocity, 
            damping, 
            frequency, 
            kfreq
        ])

    # (E) Append mass entry.  We don’t know flutter_speed or flutter_frequency yet — leave them None for now.
    flutter_mass_data.append([root_name, None, mass, None])

# ───────────────────────────────────────────────────────────────
# 2) Sort both lists.  We want to sort by:
#    (1) The integer portion of root_name (if it exists), and
#    (2) The Mach number (as float) if it exists, else 0.0.
#
#    If root_name is "optimal_solution80", then extracting
#    int(root_name.split('_')[0]) will fail.  Instead, we can:
#      • try to parse leading digits from root_name as an integer, else 0
#      • parse trailing digits after the last non‐digit as Mach.
# ───────────────────────────────────────────────────────────────

def sort_key_extracted(row):
    idx_str = row[0]                  # e.g. "optimal_solution80"
    # Try to pull any leading digits as an integer; if none, zero
    m_lead = re.match(r"^(\d+)", idx_str)
    lead_int = int(m_lead.group(1)) if m_lead else 0

    # Try to pull trailing digits as float (Mach)
    m_trail = re.search(r"(\d+)$", idx_str)
    mach_val = float(m_trail.group(1)) if m_trail else 0.0

    return (lead_int, mach_val)

def sort_key_flutter_mass(row):
    idx_str = row[0]
    m_lead = re.match(r"^(\d+)", idx_str)
    lead_int = int(m_lead.group(1)) if m_lead else 0
    m_trail = re.search(r"(\d+)$", idx_str)
    mach_val = float(m_trail.group(1)) if m_trail else 0.0
    return (lead_int, mach_val)

extracted_data.sort(key=sort_key_extracted)
flutter_mass_data.sort(key=sort_key_flutter_mass)

# ───────────────────────────────────────────────────────────────
# 3) Write out to CSV
# ───────────────────────────────────────────────────────────────
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

# ───────────────────────────────────────────────────────────────
# 4) Now interpolate flutter_speed and flutter_frequency from extracted_data
#    (exactly as before, no change required here)
# ───────────────────────────────────────────────────────────────
def interpolate_flutter_point(v1, d1, v2, d2, f1, f2):
    if d1 >= 0 or d2 <= 0:  # only when damping crosses from negative to positive
        return None, None
    flutter_speed = v1 - d1*(v2 - v1)/(d2 - d1)
    flutter_frequency = f1 + (f2 - f1)*(flutter_speed - v1)/(v2 - v1)
    return flutter_speed, flutter_frequency

def find_flutter_speed_from_csv(data_csv_file, flutter_csv_file):
    df_data = pd.read_csv(data_csv_file)
    flutter_speeds = []

    for idx, group in df_data.groupby('Index'):
        min_flutter_speed     = None
        min_flutter_frequency = None

        for mode in group['Mode'].unique():
            mode_data = group[group['Mode'] == mode]
            mode_data = mode_data.sort_values(by='Velocity')

                # … inside find_flutter_speed_from_csv(…):
            for i in range(1, len(mode_data)):
                v1     = mode_data.iloc[i-1]['Velocity']
                d1     = mode_data.iloc[i-1]['Damping']
                v2     = mode_data.iloc[i  ]['Velocity']
                d2     = mode_data.iloc[i  ]['Damping']
                f1     = mode_data.iloc[i-1]['Frequency']
                f2     = mode_data.iloc[i  ]['Frequency']
                # kfreq2 = mode_data.iloc[i  ]['Kfreq']
                
                # ↓ Remove this guard so we don’t skip rows just because Kfreq==0:
                # if kfreq2 == 0:
                #     continue

                flutter_speed, flutter_frequency = interpolate_flutter_point(v1, d1, v2, d2, f1, f2)
                if flutter_speed is not None:
                    if min_flutter_speed is None or flutter_speed < min_flutter_speed:
                        min_flutter_speed     = flutter_speed
                        min_flutter_frequency = flutter_frequency
                    break


                flutter_speed, flutter_frequency = interpolate_flutter_point(v1, d1, v2, d2, f1, f2)
                if flutter_speed is not None:
                    if min_flutter_speed is None or flutter_speed < min_flutter_speed:
                        min_flutter_speed     = flutter_speed
                        min_flutter_frequency = flutter_frequency
                        print(f"Interpolated flutter speed for {idx}, mode {mode}: {flutter_speed:.3f}, frequency: {flutter_frequency:.3f}")
                    break

        if min_flutter_speed is not None:
            flutter_speeds.append((idx, min_flutter_speed, min_flutter_frequency))

    # Now merge those results back into flutter_speeds_and_mass.csv
    df_flutter = pd.read_csv(flutter_csv_file)
    flutter_dict = {x[0]:(x[1], x[2]) for x in flutter_speeds}
    df_flutter['Flutter Speed']     = df_flutter['Index'].map(lambda x: flutter_dict[x][0] if x in flutter_dict else None)
    df_flutter['Flutter Frequency'] = df_flutter['Index'].map(lambda x: flutter_dict[x][1] if x in flutter_dict else None)
    df_flutter.to_csv(flutter_csv_file, index=False)

    print(f"Updated flutter speeds and frequencies have been saved to '{flutter_csv_file}'")

find_flutter_speed_from_csv(data_csv_file, flutter_csv_file)

# ───────────────────────────────────────────────────────────────
# 5) Finally, plot graphs (no change needed here)
# ───────────────────────────────────────────────────────────────
def plot_graphs(extracted_data, flutter_csv_file):
    flutter_data = pd.read_csv(flutter_csv_file)

    for idx, flutter_speed, mass, flutter_frequency in flutter_data.itertuples(index=False):
        data_rows = [row for row in extracted_data if row[0] == idx]
        if not data_rows:
            continue

        modes = sorted(set(row[1] for row in data_rows))

        plt.figure(figsize=(10, 12))

        # (a) Velocity vs. Damping plot
        plt.subplot(2, 1, 1)
        for mode in modes:
            mode_data = [row for row in data_rows if row[1] == mode]
            velocities = [row[2] for row in mode_data]
            dampings   = [row[3] for row in mode_data]
            plt.plot(velocities, dampings, label=mode)
        if flutter_speed:
            plt.axvline(x=flutter_speed, color='r', linestyle='--', label='Flutter Speed')
            plt.text(flutter_speed + 5, 0.1,
                     f'Flutter Speed = {flutter_speed:.2f}',
                     color='black', fontsize=12, fontweight='bold',
                     verticalalignment='bottom', horizontalalignment='left',
                     bbox=dict(facecolor='white', alpha=0.5))
        plt.axhline(y=0, color='black', linestyle='--', label='Zero Damping')
        plt.xlabel('Velocity')
        plt.ylabel('Damping')
        plt.ylim(-1, 1)
        plt.title('Velocity vs. Damping')
        plt.legend()
        plt.grid(True)

        # (b) Velocity vs. Frequency plot
        plt.subplot(2, 1, 2)
        for mode in modes:
            mode_data = [row for row in data_rows if row[1] == mode]
            velocities = [row[2] for row in mode_data]
            frequencies = [row[4] for row in mode_data]
            plt.plot(velocities, frequencies, label=mode)
        if flutter_speed and flutter_frequency:
            plt.axvline(x=flutter_speed, color='r', linestyle='--', label='Flutter Speed')
            plt.axhline(y=flutter_frequency, color='g', linestyle='--', label='Flutter Frequency')
            plt.text(flutter_speed + 5, flutter_frequency + 1,
                     f'Flutter Frequency = {flutter_frequency:.2f}',
                     color='black', fontsize=12, fontweight='bold',
                     verticalalignment='bottom', horizontalalignment='left',
                     bbox=dict(facecolor='white', alpha=0.5))
            # Optionally zoom in around the flutter point
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
        plt.savefig(os.path.join(graph_dir, f'{idx}.png'))
        plt.close()

plot_graphs(extracted_data, flutter_csv_file)

# ───────────────────────────────────────────────────────────────
# 6) Combine sample_parameter.csv with flutter_speeds_and_mass.csv
# ───────────────────────────────────────────────────────────────

params_file  = 'sample_parameters.csv'
flutter_file = 'flutter_speeds_and_mass.csv'
out_file     = 'combined_last.csv'

df_params  = pd.read_csv(params_file)
df_flutter = pd.read_csv(flutter_file)

# drop the Index column entirely
df_params = df_params.drop(columns=['Index'])
# pick only the flutter columns
df_flutter = df_flutter[['Flutter Speed', 'Mass', 'Flutter Frequency']]

# concatenate side-by-side
df_combined = pd.concat([df_params, df_flutter], axis=1)

df_combined.to_csv(out_file, index=False)
print(f"Written combined file (no Index) to '{out_file}'")
