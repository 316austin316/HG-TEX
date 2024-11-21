Haunting Ground TEX Importer/Exporter

This tool allows users to extract textures from .TEX files into editable .BMP format and import modified .BMP images back into .TEX files.
Features

    Export Textures: Extract textures from .TEX files and save them as .BMP images.
    Import Textures: Import edited .BMP images and generate a new .TEX file.
    Supports 4bpp and 8bpp Formats: Handles textures with both 4 bits per pixel (bpp) and 8 bpp formats.

Usage

    GUI Interface:

        Export Textures:
            Click on "Export Textures".
            Select the .TEX file you want to export textures from.
            The script will process the file and export .BMP and CLUT (.bin) files in the same directory.
            A message will appear confirming the export completion.

        Import Textures:
            Click on "Import Textures".
            Select the .BMP files you want to import (you can select multiple files).
            Select a reference .TEX file (used to read headers).
            Choose a location and name for the output .TEX file.
            The script will process the .BMP files and create a new .TEX file.
            A message will appear confirming the import completion.


Notes

    For importing textures, the reference .TEX file is necessary to preserve the correct headers and unknown bytes.


TL;DR:

Exporting Textures

    Select .TEX File:

    Exported .BMP Files:

Importing Textures

    Select .BMP Files:

    Select Reference .TEX File:

    Save Output .TEX File:
