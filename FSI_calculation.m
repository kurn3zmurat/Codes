main_matrix=[   -1.9548362E-01,1.1849423E-01,2.1000000E+02,2.2500000E+02;
                -1.1130910E-01,1.6390591E-01,2.1000000E+02,2.2500000E+02; 
                -1.0533046E-01,1.0209930E-02,1.95000000E+02,2.1000000E+02;
                -5.8782228E-02,5.4779891E-03,1.8000000E+02,1.9500000E+02;
                -3.4548410E-02,2.4351608E-02,1.8000000E+02,1.9500000E+02;
                -2.2966491E-02,1.6367914E-02,2.1000000E+02,2.2500000E+02];
%burada çıkan sonuçları matris içine koydum interpolasyon için
length=size(main_matrix,1);
flutter_speed = zeros(1, length);
for i=1:length
    flutter_speed(i)=Interpolation(main_matrix(i,1),main_matrix(i,2), main_matrix(i,3),main_matrix(i,4), 0);
end

% Load CSV data
data = readmatrix('plotting.csv');

% Extract FSI values for each method (assuming the second column is FSI)
experiment_FSI = data(1:5, 2);
euler_tm_FSI = data(6:10, 2);
rans_tm_FSI = data(11:15, 2);
nastran_dlm_FSI = data(16:20, 2);
goura_euler_FSI = data(21:25, 2);

% Define Mach numbers (assuming they are the same for all methods)
mach_numbers = data(1:5, 1);

% Plot the data for each method
figure;
hold on;

% Plot Experiment data
plot(mach_numbers, experiment_FSI, 'kx-', 'DisplayName', 'Experiment');

% Plot Time Marching, Euler data
plot(mach_numbers, euler_tm_FSI, 'ks-', 'DisplayName', 'Time Marching, Euler');

% Plot Time Marching, RANS data
plot(mach_numbers, rans_tm_FSI, 'ko-', 'DisplayName', 'Time Marching, RANS');

% Plot Nastran DLM data
plot(mach_numbers, nastran_dlm_FSI, 'kd-', 'DisplayName', 'Nastran DLM');

% Plot Goura, Euler data
plot(mach_numbers, goura_euler_FSI, 'k^-', 'DisplayName', 'Goura, Euler');

% Compute FSI values
mach_numbers = [0.45, 0.6, 0.75, 0.9, 0.95, 1.05];
dens = 1.225;
omega = 3.969916E+01 * 2 * pi;
b_s = 0.2794;
b_t = 0.1841;
span = 0.762;
m = 1.862;
V = pi / 3 * span * ((b_t + b_s)^2 - b_t * b_s);
p_d = (1 / 2 * dens) .* flutter_speed.^2;
FSI = (2 .* p_d).^(0.5) ./ (b_s * omega * (m / V)^0.5);

% Spline for smoother curve
mach_numbers_spline = linspace(0.45, 1.05, 100); % Daha düzgün bir grafik için x değerlerini artırma
FSI_spline = spline(mach_numbers, FSI/2, mach_numbers_spline);

% Plot your computed FSI values
plot(mach_numbers_spline, FSI_spline, 'b-', 'HandleVisibility', 'off'); % Don't show the line in legend
plot(mach_numbers, FSI/2, 'bp', 'DisplayName', 'PKE-method, DLM'); % Use star marker for data points

% Add labels, legend, and title
xlabel("Mach Numbers");
ylabel("FSI");
legend('show', 'Location', 'best'); % Puts the legend inside the plot for clarity
title('FSI Comparison');

hold off;

% Function for interpolation
function y = Interpolation(x1, x2, y1, y2, x)
    y = y1 + (y2 - y1) / (x2 - x1) * (x - x1);
end
