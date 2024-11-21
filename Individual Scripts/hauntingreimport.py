import re
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import filedialog

def import_textures(bmp_files, reference_tex_file, output_tex_file):
    textures_data = []

    # Sort bmp_files based on numbers in filenames
    def extract_number(filename):
        match = re.search(r'(\d+)', filename)
        return int(match.group(1)) if match else 0

    bmp_files = sorted(bmp_files, key=lambda x: extract_number(x))

    # Open the reference TEX file to read headers and unknown bytes
    with open(reference_tex_file, 'rb') as ref_file:
        num_textures_ref = int.from_bytes(ref_file.read(1), 'big')
        ref_file.seek(0x10)  # Move to the start of the first texture header

        # Read all headers from the reference TEX file
        reference_headers = []
        for i in range(num_textures_ref):
            header = ref_file.read(16)
            reference_headers.append(header)

    # Ensure we have enough reference headers
    if len(reference_headers) < len(bmp_files):
        print("Not enough headers in the reference TEX file for the number of BMP files.")
        exit()

    for idx, bmp_file in enumerate(bmp_files):
        # Load the BMP image and ensure it's in palette mode to access indices and palette
        image = Image.open(bmp_file).convert('P')
        width, height = image.size
        pixels = np.array(image)
        
        # Check format flag from the reference header
        reference_header = reference_headers[idx]
        format_flag_value = int.from_bytes(reference_header[0:4], 'little')
        is_4bpp = format_flag_value == 0x14  # Assume 0x14 means 4bpp

        # Invert grayscale values for BMP to TEX format compatibility
        pixels = 255 - pixels

        # Read the palette from the BMP image
        palette = image.getpalette()  # This returns a list of RGB values

        # Determine the number of colors to extract based on 4bpp or 8bpp format
        num_colors = 16 if is_4bpp else 256  # 16 colors for 4bpp, 256 for 8bpp
        clut_data_raw = palette[:num_colors * 3]  # Extract colors for the CLUT
        clut_data = []

        # Convert to RGBA, set alpha as 0x80 for non-zero entries as specified
        for i in range(0, num_colors * 3, 3):
            r, g, b = clut_data_raw[i], clut_data_raw[i + 1], clut_data_raw[i + 2]
            alpha = 0x80 if (r, g, b) != (0, 0, 0) else 0x00  # Alpha as 0x80 if color isn't black
            clut_data.append((r, g, b, alpha))

        # Flip the CLUT as specified
        flipped_clut = clut_data[::-1]

        # Handle the twiddling and padding of CLUT based on format
        if is_4bpp:
            # For 4bpp, create two sections with a 32-byte gap in between
            section1 = flipped_clut[:8]
            section2 = flipped_clut[8:]
            combined_clut = section1 + [(0x00, 0x00, 0x00, 0x00)] * 8 + section2  # Insert 32-byte gap

            # Pad the CLUT to 1024 bytes
            padded_clut = combined_clut + [(0x00, 0x00, 0x00, 0x00)] * (256 - len(combined_clut))
            bpp = 4
        else:
            # Use full 8bpp CLUT without additional padding
            clut_entries = flipped_clut  # Already flipped, contains 256 entries
            clut_twiddled = []
            for i in range(0, 256, 32):
                clut_twiddled.extend(clut_entries[i:i+8])     # Colors 0-7
                clut_twiddled.extend(clut_entries[i+16:i+24]) # Colors 16-23
                clut_twiddled.extend(clut_entries[i+8:i+16])  # Colors 8-15
                clut_twiddled.extend(clut_entries[i+24:i+32]) # Colors 24-31
            padded_clut = clut_twiddled  # Already 1024 bytes for 8bpp
            bpp = 8

        # Convert indexed pixels to binary format based on bits per pixel
        pixel_data = bytearray()
        if bpp == 4:
            # Pack two 4-bit indices per byte for 4bpp format
            for y in range(height):
                for x in range(0, width, 2):
                    low_nibble = pixels[y, x] & 0x0F
                    high_nibble = (pixels[y, x + 1] & 0x0F) if (x + 1) < width else 0
                    pixel_data.append((high_nibble << 4) | low_nibble)
        else:  # 8bpp format
            for y in range(height):
                for x in range(width):
                    pixel_data.append(pixels[y, x])

        # Extract the unknown bytes from the reference header
        unknown_bytes = reference_header[8:12]

        # Store all texture data for later processing
        textures_data.append({
            'format_flag_value': format_flag_value,
            'width': width,
            'height': height,
            'bpp': bpp,
            'pixel_data': pixel_data,
            'clut_data': padded_clut,
            'unknown_bytes': unknown_bytes
        })

    # Start writing the new TEX file
    with open(output_tex_file, 'wb') as out_file:
        num_textures = len(textures_data)
        out_file.write(num_textures.to_bytes(1, 'big'))
        out_file.write(b'\x00' * 15)  # Fill the rest up to 0x10

        headers = []
        data_offset = 0x10 + num_textures * 16  # Initial data offset after headers

        # First pass: Write headers and calculate offsets
        for idx, tex in enumerate(textures_data):
            format_flag_value = tex['format_flag_value']
            width = tex['width']
            height = tex['height']
            bpp = tex['bpp']
            pixel_data_size = (width * height) // (2 if bpp == 4 else 1)

            # Create texture header
            header = bytearray(16)
            header[0:4] = format_flag_value.to_bytes(4, 'little')
            header[4:6] = width.to_bytes(2, 'little')
            header[6:8] = height.to_bytes(2, 'little')
            header[8:12] = tex['unknown_bytes']  # Include unknown bytes
            header[12:16] = (data_offset - (0x10 + idx * 16)).to_bytes(4, 'little')  # Relative data offset

            headers.append(header)

            # Update data offset for next texture
            data_offset += pixel_data_size + 1024  # Pixel data size + CLUT size

        # Second pass: Write headers
        for header in headers:
            out_file.write(header)

        # Third pass: Write pixel data and CLUTs
        for tex in textures_data:
            out_file.write(tex['pixel_data'])
            for color in tex['clut_data']:
                out_file.write(bytes(color))

    print(f"\nTextures imported and saved to {output_tex_file}")

# File selection dialogs
root = tk.Tk()
root.withdraw()  # Hide the main tkinter window

# Select multiple BMP files
bmp_files = filedialog.askopenfilenames(title="Select BMP files to import", filetypes=[("BMP Files", "*.bmp")])
if not bmp_files:
    print("No BMP files selected.")
    exit()

# Select the reference TEX file
reference_tex_file = filedialog.askopenfilename(title="Select the reference TEX file", filetypes=[("TEX Files", "*.tex")])
if not reference_tex_file:
    print("No reference TEX file selected.")
    exit()

# Select the output TEX file path
output_tex_file = filedialog.asksaveasfilename(title="Save the output TEX file", defaultextension=".tex", filetypes=[("TEX Files", "*.tex")])
if not output_tex_file:
    print("No output file path selected.")
    exit()

# Run the import process
import_textures(bmp_files, reference_tex_file, output_tex_file)
