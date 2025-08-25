
import csv
import os
from PIL import Image, ImageDraw

def generate_data(num_frames=200, output_csv='raw_positions.csv', output_image_dir='raw_images'):
    """
    Generates simulated vehicle position data and corresponding images.

    Args:
        num_frames (int): The number of frames (and data points) to generate.
        output_csv (str): The name of the output CSV file for position data.
        output_image_dir (str): The name of the directory to save generated images.
    """
    # Get the directory where the script is located to make paths relative
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, output_csv)
    image_dir_path = os.path.join(script_dir, output_image_dir)

    # Create the output directory for images if it doesn't exist
    if not os.path.exists(image_dir_path):
        os.makedirs(image_dir_path)

    # --- 1. Generate Position Data ---
    positions = []
    start_time = 1672531200  # Example start time (Unix timestamp)
    time_increment_ms = 100  # 100ms between frames

    for i in range(num_frames):
        timestamp = start_time + (i * time_increment_ms) / 1000.0
        x = 50 + i * 2  # Move along x-axis
        y = 100 + int(0.01 * (i*2) ** 2)  # Move in a curve along y-axis
        positions.append({'timestamp': timestamp, 'x': x, 'y': y, 'frame': i})

    # Write to CSV
    with open(csv_path, 'w', newline='') as csvfile:
        fieldnames = ['timestamp', 'x', 'y']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for pos in positions:
            writer.writerow({'timestamp': pos['timestamp'], 'x': pos['x'], 'y': pos['y']})

    print(f"Successfully generated position data in '{csv_path}'")

    # --- 2. Generate Image Data ---
    img_width, img_height = 800, 600
    for pos in positions:
        img = Image.new('RGB', (img_width, img_height), 'white')
        draw = ImageDraw.Draw(img)

        vehicle_radius = 10
        draw_x, draw_y = pos['x'], img_height - pos['y']
        
        bbox = [
            (draw_x - vehicle_radius, draw_y - vehicle_radius),
            (draw_x + vehicle_radius, draw_y + vehicle_radius)
        ]
        draw.ellipse(bbox, fill='blue', outline='black')
        
        draw.text((10, 10), f"Timestamp: {pos['timestamp']:.2f}", fill="black")

        image_path = os.path.join(image_dir_path, f"frame_{pos['frame']:04d}.png")
        img.save(image_path)

    print(f"Successfully generated {num_frames} image frames in '{image_dir_path}/'")

if __name__ == '__main__':
    # Ensure Pillow is installed
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow library not found. Please install it using: pip install Pillow")
        exit(1)
    generate_data()

