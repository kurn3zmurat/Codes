import numpy as np
import os
import csv
import subprocess
from multiprocessing import Pool

#-------------------------------------
# Define Variable Limits
#-------------------------------------
VarLim = np.zeros((3, 2))
VarLim[0, :] = [6.2e10, 8e10]     # Young's Modulus 3
VarLim[1, :] = [850, 1010]        # Density 1
VarLim[2, :] = [2645, 2945]       # Density 3

#-------------------------------------
# Read and Scale Sampling
#-------------------------------------
smplName = "halton_samples_new.csv"
with open(smplName, newline='') as csvfile:
    data = list(csv.reader(csvfile))
    Nvar = len(data[0])
    NSamples = len(data)

VarN = np.zeros((Nvar, NSamples))
Var = np.zeros((Nvar, NSamples))
with open(smplName, newline='') as csvfile:
    data = list(csv.reader(csvfile))
    for i in range(NSamples):
        a = data[i]
        for j in range(Nvar):
            VarN[j, i] = float(a[j])

for i in range(Nvar):
    Var[i, :] = np.interp(VarN[i, :], (VarN[i, :].min(), VarN[i, :].max()), (VarLim[i, 0], VarLim[i, 1]))
samples = Var.T[:150]

#-------------------------------------
# Read the base input file
#-------------------------------------
with open('sol145_combined3D_new.dat', 'r') as file:
    base_content = file.read()

# Function to modify content with real formatting and dummy fillers
def modify_content(content, E3, rho1, rho3):
    content = content.replace('E3Plc', f'{E3:.3e}')
    content = content.replace('rho1Plc', f'{rho1:.4f}')
    content = content.replace('rho3Plc', f'{rho3:.4f}')

    # Dummy replacement for unused variables
    for i in [1, 2, 4, 5]:
        content = content.replace(f'E{i}Plc', '1.000e+09')
        content = content.replace(f'rho{i}Plc', '1.0000')
    for i in range(1, 6):
        content = content.replace(f'P{i}Plc', '0.350')

    return content

#-------------------------------------
# Paths and Settings
#-------------------------------------
input_dir = 'generated_inputs'
output_dir = 'generated_outputs'
os.makedirs(input_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

mach_values = [0.15]
nastran_executable = r'C:\Program Files\MSC.Software\MSC_Nastran\2024.2\bin\nastran.exe'

#-------------------------------------
# Nastran Runner
#-------------------------------------
def run_nastran(case):
    i, sample = case
    E3, rho1, rho3 = sample
    case_dir = os.path.join(input_dir, f'Case_{i}')
    os.makedirs(case_dir, exist_ok=True)
    sample_data = []

    for mach in mach_values:
        new_content = modify_content(base_content.replace('MachPlc', f'{mach:.3f}'), E3, rho1, rho3)
        filename = f'{i}_M{mach:.3f}.dat'
        filepath = os.path.join(case_dir, filename)

        with open(filepath, 'w') as file:
            file.write(new_content)

        # Run Nastran
        abs_case = os.path.abspath(case_dir)
        scr_opt = f"scr={abs_case}"

        result = subprocess.run(
            [nastran_executable, filename, scr_opt],
            cwd=case_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        # Optional fallback (some versions need this)
        subprocess.run([nastran_executable, filename], cwd=case_dir)

        # Clean unnecessary files
        for fname in os.listdir(case_dir):
            if fname.endswith(".f04") or fname.endswith(".log"):
                try:
                    os.remove(os.path.join(case_dir, fname))
                except Exception:
                    pass

        # Move f06 output
        try:
            src = os.path.join(case_dir, filename.replace('.dat', '.f06'))
            dst = os.path.join(output_dir, f'{i}_M{mach:.3f}.f06')
            os.rename(src, dst)
        except FileNotFoundError:
            pass

        sample_data.append([f'{i}_M{mach:.1f}', mach, E3, rho1, rho3])

    return sample_data

#-------------------------------------
# Parallel Execution
#-------------------------------------
if __name__ == '__main__':
    with Pool(processes=5) as pool:
        all_sample_data = pool.map(run_nastran, enumerate(samples))

    flat_sample_data = [item for sublist in all_sample_data for item in sublist]

    csv_file = 'sample_parameters.csv'
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Index', 'Mach', 'YoungsModulus3', 'Density1', 'Density3'])
        for row in flat_sample_data:
            formatted_row = [f'{val:.3f}' if isinstance(val, float) else val for val in row]
            writer.writerow(formatted_row)

    print(f"✅ {len(samples) * len(mach_values)} input files generated.")
    print(f"📝 Parameters saved to '{csv_file}'")
    print(f"📂 Output files moved to '{output_dir}'")
