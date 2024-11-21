import numpy as np
import matplotlib.pyplot as plt
import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image

# Function to parse, visualize, and export textures from file
def visualize_and_export_textures(file_path):
    # Read the file header to determine format and dimensions
    with open(file_path, 'rb') as file:
        # Read the number of textures
        num_textures = int.from_bytes(file.read(1), 'big')
        print(f"Number of textures: {num_textures}")
        file.seek(0x10)  # Move to the start of the first texture header

        # Read all texture headers and determine data positions
        headers = []
        data_offsets = []
        for i in range(num_textures):
            header = file.read(16)
            headers.append(header)
            print(f"Header {i + 1}: {header.hex()}")

            # Extract the data position relative to the start of this header
            relative_data_offset = int.from_bytes(header[12:16], 'little')
            data_offsets.append(0x10 + i * 16 + relative_data_offset)
            print(f"Data offset for texture {i + 1}: {hex(data_offsets[-1])}")

        for idx, header in enumerate(headers):
            # Extract texture-specific properties
            format_flag = header[0x00:0x04]
            format_flag_value = int.from_bytes(format_flag, 'little')
            width = int.from_bytes(header[0x04:0x06], 'little')
            height = int.from_bytes(header[0x06:0x08], 'little')
            print(f"\nTexture {idx + 1} dimensions: {width}x{height}")
            print(f"Format flag value: {format_flag_value}")

            # Determine bits per pixel based on the format flag
            if format_flag_value == 0x13:
                bpp = 8
            elif format_flag_value == 0x14:
                bpp = 4
            else:
                raise ValueError(f"Unsupported format flag: {format_flag_value}")
            print(f"Bits per pixel for texture {idx + 1}: {bpp}")

            # Calculate pixel data size based on bpp
            pixel_data_size = (width * height) // (2 if bpp == 4 else 1)
            print(f"Pixel data size for texture {idx + 1}: {pixel_data_size} bytes")

            # Read the pixel data from the offset specified in the header
            file.seek(data_offsets[idx])
            pixel_data = file.read(pixel_data_size)

            # Read CLUT if applicable (starting after pixel data)
            clut_start_offset = data_offsets[idx] + pixel_data_size
            clut_size = 1024  # 256 colors * 4 bytes per color (RGBA)
            print(f"CLUT for texture {idx + 1} starts at: {hex(clut_start_offset)}, size: {clut_size} bytes")
            file.seek(clut_start_offset)
            clut_data_raw = file.read(clut_size)

            # Parse CLUT data into RGBA colors and scale alpha
            clut_entries = [clut_data_raw[i:i+4] for i in range(0, len(clut_data_raw), 4)]
            clut_twiddled = []
            for i in range(0, 256, 32):
                clut_twiddled.extend(clut_entries[i:i+8])    # 0-7
                clut_twiddled.extend(clut_entries[i+16:i+24]) # 16-23
                clut_twiddled.extend(clut_entries[i+8:i+16])  # 8-15
                clut_twiddled.extend(clut_entries[i+24:i+32]) # 24-31
            
            # Scale alpha and construct RGBA colors
            clut_data = [
                (entry[0], entry[1], entry[2], min(entry[3] * 2, 255))  # Scale alpha by 2
                for entry in clut_twiddled
            ]

            # Export the processed CLUT data
            clut_output_file = f"{os.path.splitext(os.path.basename(file_path))[0]}_texture{idx + 1}_clut.bin"
            with open(clut_output_file, 'wb') as clut_file:
                for color in clut_data:
                    clut_file.write(bytes(color))
            print(f"Exported processed CLUT for texture {idx + 1} as {clut_output_file}")

            # Prepare expanded pixel array for RGBA
            expanded_pixels = np.zeros((height, width, 4), dtype=np.uint8)

            # Map the pixel data using the twiddled CLUT
            if bpp == 4:
                for i in range(pixel_data_size):
                    low_nibble = pixel_data[i] & 0x0F
                    high_nibble = (pixel_data[i] & 0xF0) >> 4
                    y, x = divmod(2 * i, width)
                    if y < height:
                        if low_nibble < len(clut_data):
                            expanded_pixels[y, x] = clut_data[low_nibble]
                        if x + 1 < width and high_nibble < len(clut_data):
                            expanded_pixels[y, x + 1] = clut_data[high_nibble]
            else:
                for i in range(pixel_data_size):
                    pixel_value = pixel_data[i]
                    if pixel_value < len(clut_data):
                        expanded_pixels[i // width, i % width] = clut_data[pixel_value]

            # Create BMP file with indexed colors
            bmp_output_file = f"{os.path.splitext(os.path.basename(file_path))[0]}_texture{idx + 1}.bmp"
            image = Image.fromarray(expanded_pixels[..., :3], 'RGB')
            image = image.convert('P', palette=Image.ADAPTIVE, colors=256)  # Convert to indexed BMP
            image.save(bmp_output_file, format='BMP')
            print(f"Exported texture {idx + 1} as {bmp_output_file}")

# File selection dialog to select a file dynamically
root = tk.Tk()
root.withdraw()  # Hide the main tkinter window
file_path = filedialog.askopenfilename(title="Select a Texture File", filetypes=[("Texture Files", "*.TEX"), ("All Files", "*.*")])

if file_path:
    visualize_and_export_textures(file_path)
else:
    print("No file selected.")
