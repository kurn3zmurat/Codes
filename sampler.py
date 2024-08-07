import numpy as np
import os
import csv
import subprocess
from multiprocessing import Pool

#-------------------------------------
# Define Variable Limits
#-------------------------------------
VarLim = np.zeros((15, 2))

# Interval
VarLim[0, :] = [0.35, 0.45]  # camber 1
VarLim[1, :] = [0.35, 0.45]  # camber 2
VarLim[2, :] = [0.30, 0.36]  # camber 3
VarLim[3, :] = [0.25, 0.35]  # Sweep, 3rd and 4th partitions Wing
VarLim[4, :] = [0.35, 0.45]  # Twist, 3rd Airfoil
VarLim[5, :] = [0.8e9, 1.4e9]  # Twist, 4th Airfoil
VarLim[6, :] = [3.5e8, 6.0e8]  # Twist, 5th Airfoil
VarLim[7, :] = [5.5e10, 8.5e10]  # Span, 3rd Partition
VarLim[8, :] = [0.7e6, 1.3e6]  # Span, 4th Partition
VarLim[9, :] = [0.8e9, 1.4e9]  # X position, H_tail
VarLim[10, :] = [870, 990]  # Sweep, h_tail
VarLim[11, :] = [0.01, 0.05]  # Incidence Angle, h_tail
VarLim[12, :] = [2700, 2950]  # Nose z position, fuselage
VarLim[13, :] = [0.0005, 0.0015]  # d2 x position, fuselage
VarLim[14, :] = [870, 990]  # d2 diameter, fuselage

#-------------------------------------
# Read and Scale Sampling
#-------------------------------------
# Sampling file name
i_ini = 0  # int(sys.argv[1]) #input("Initial: ")
i_fin = 200  # int(sys.argv[2]) #input("Final: ")
smplName = "halton_samples.csv"  # str(sys.argv[3]) 

# Find number of samples
with open(smplName, newline='') as csvfile:
    data = list(csv.reader(csvfile))
    a1 = data[0]
    Nvar = len(a1)
    NSamples = len(data)

VarN = np.zeros((Nvar, NSamples))  # Normalized variable array
Var = np.zeros((Nvar, NSamples))  # Variable array
with open(smplName, newline='') as csvfile:
    data = list(csv.reader(csvfile))
    for i in range(NSamples):
        a = data[i]
        for j in range(Nvar):
            VarN[j, i] = a[j]

for i in range(Nvar):
    Var[i, :] = np.interp(VarN[i, :], (VarN[i, :].min(), VarN[i, :].max()), (VarLim[i, 0], VarLim[i, 1]))
samples = Var.T[:200]  # Limit to the first 50 samples

# Read the base input file
with open('sol145_combined3D.dat', 'r') as file:
    base_content = file.read()

# Function to modify content with new parameters
def modify_content(content, poisson_values, youngs_modulus_values, density_values):
    for i in range(1, 6):
        content = content.replace(f'P{i}Plc', f'{poisson_values[i-1]:.3f}')
        content = content.replace(f'E{i}Plc', f'{youngs_modulus_values[i-1]:.3e}')
        content = content.replace(f'rho{i}Plc', f'{density_values[i-1]:.4f}')
    return content

# Directory to save new input files and outputs
input_dir = 'generated_inputs'
output_dir = 'generated_outputs'
os.makedirs(input_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

mach_values = [0.001, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
nastran_executable = r'C:\Program Files\MSC.Software\MSC_Nastran\2023.2\bin\nastran.exe'

def run_nastran(case):
    i, sample = case
    poisson_values = sample[:5]
    youngs_modulus_values = sample[5:10]
    density_values = sample[10:]
    case_dir = os.path.join(input_dir, f'Case_{i+39}')
    os.makedirs(case_dir, exist_ok=True)
    sample_data = []
    
    for mach in mach_values:
        new_content = modify_content(base_content.replace('MachPlc', f'{mach:.3f}'), poisson_values, youngs_modulus_values, density_values)
        filename = f'{i+39}_M{mach:.3f}.dat'
        filepath = os.path.join(case_dir, filename)
        
        with open(filepath, 'w') as file:
            file.write(new_content)
        
        # Run Nastran analysis
        subprocess.run([nastran_executable, filename], cwd=case_dir)
        
        # Move output files to the output directory
        for ext in ['.f06', '.f04', '.log', '.xdb']:
            try:
                src = os.path.join(case_dir, filename.replace('.dat', ext))
                dst = os.path.join(output_dir, f'{i+39}_M{mach:.3f}{ext}')
                os.rename(src, dst)
            except FileNotFoundError:
                pass  # Ignore if the file does not exist
        
        # Remove unnecessary output files
        for ext in ['.f04', '.log', '.xdb']:
            try:
                os.remove(os.path.join(output_dir, f'{i+39}_M{mach:.3f}{ext}'))
            except FileNotFoundError:
                pass  # Ignore if the file does not exist
        
        sample_data.append([f'{i+39}_M{mach:.1f}', mach] + list(poisson_values) + list(youngs_modulus_values) + list(density_values))
    
    return sample_data

# Use multiprocessing Pool to run Nastran in parallel
if __name__ == '__main__':
    with Pool(processes=3) as pool:
        all_sample_data = pool.map(run_nastran, enumerate(samples))
    
    # Flatten the list of lists
    flat_sample_data = [item for sublist in all_sample_data for item in sublist]
    
    # Save sample data to CSV with 3 decimal places
    csv_file = 'sample_parameters.csv'
    columns = ['Index', 'Mach', 'Poisson1', 'Poisson2', 'Poisson3', 'Poisson4', 'Poisson5', 'YoungsModulus1', 'YoungsModulus2', 'YoungsModulus3', 'YoungsModulus4', 'YoungsModulus5', 'Density1', 'Density2', 'Density3', 'Density4', 'Density5']
    
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        for row in flat_sample_data:
            formatted_row = [f'{val:.3f}' if isinstance(val, float) else val for val in row]
            writer.writerow(formatted_row)
    
    print(f"Generated {len(samples) * len(mach_values)} input files in {input_dir} and saved parameters to '{csv_file}'")
    print(f"Output files have been moved to '{output_dir}'")
