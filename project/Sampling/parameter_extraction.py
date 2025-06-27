import os
import re
import csv

# Function to read parameters from an input file
def read_parameters(filepath):
    parameters = {}
    with open(filepath, 'r') as file:
        lines = file.readlines()
        
        # Extract Mach number from the filename
        mach_match = re.search(r'M(\d+\.\d+)', filepath)
        if mach_match:
            parameters['Mach'] = float(mach_match.group(1))
        
        # Extract Young's Modulus, Poisson's Ratio, and Density
        mat_count = 1
        for i, line in enumerate(lines):
            if 'MAT1*' in line:
                try:
                    youngs_modulus = float(lines[i].split()[2])
                    poisson_ratio = float(lines[i].split()[4])
                    density = float(lines[i + 1].split()[1])
                    
                    parameters[f'YoungsModulus{mat_count}'] = youngs_modulus
                    parameters[f'Poisson{mat_count}'] = poisson_ratio
                    parameters[f'Density{mat_count}'] = density
                    
                    mat_count += 1
                except (IndexError, ValueError):
                    continue
    
    return parameters

# Directory containing the input files
input_dir = 'generated_inputs'

# Collect all parameter data
all_parameters = []
for root, dirs, files in os.walk(input_dir):
    for file in files:
        if file.endswith('.dat'):
            filepath = os.path.join(root, file)
            parameters = read_parameters(filepath)
            parameters['Filename'] = file
            all_parameters.append(parameters)

# Print all collected parameters
for param in all_parameters:
    print(param)

# If needed, save the parameters to a CSV file
csv_file = 'extracted_parameters.csv'
columns = ['Filename', 'Mach', 'YoungsModulus1', 'Poisson1', 'Density1', 'YoungsModulus2', 'Poisson2', 'Density2', 
           'YoungsModulus3', 'Poisson3', 'Density3', 'YoungsModulus4', 'Poisson4', 'Density4', 'YoungsModulus5', 
           'Poisson5', 'Density5']

with open(csv_file, 'w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    for param in all_parameters:
        writer.writerow(param)

print(f"Extracted parameters have been saved to '{csv_file}'")