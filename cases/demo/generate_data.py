
import numpy as np
import pandas as pd
import os

# Simulation parameters
dt = 0.02  # 20ms
num_points = 100
total_time = num_points * dt
initial_pos = np.array([0.0, 0.0])
initial_speed = 10.0  # m/s
initial_direction = np.deg2rad(30) # 30 degrees
turn_rate = np.deg2rad(2) # 2 degrees per second

# Noise parameters
position_noise_std = 0.5 # meters

# Generate data
timestamps = np.arange(0, total_time, dt)
positions = np.zeros((num_points, 2))
directions = np.zeros(num_points)
speeds = np.full(num_points, initial_speed)

current_pos = initial_pos
current_direction = initial_direction

for i in range(num_points):
    # Update direction
    current_direction += turn_rate * dt
    
    # Update position
    velocity = np.array([initial_speed * np.cos(current_direction),
                         initial_speed * np.sin(current_direction)])
    current_pos += velocity * dt
    
    # Store data
    positions[i] = current_pos
    directions[i] = np.rad2deg(current_direction) # store in degrees

# Add noise to position
noisy_positions = positions + np.random.normal(0, position_noise_std, size=positions.shape)

# Create DataFrame
df = pd.DataFrame({
    'timestamp': timestamps,
    'x_actual': noisy_positions[:, 0],
    'y_actual': noisy_positions[:, 1],
    'speed': speeds,
    'direction': directions
})

# Define output path and save to CSV
output_path = os.path.join('cases', 'demo', 'car_info.csv')
df.to_csv(output_path, index=False)

print(f"Successfully generated {num_points} data points to {output_path}")
