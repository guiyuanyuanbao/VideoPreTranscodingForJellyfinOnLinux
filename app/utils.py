# app/utils.py
import os
from zipfile import ZipFile

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
ZIP_DIR = "zips"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ZIP_DIR, exist_ok=True)

def create_zip(file_paths, zip_name):
    zip_path = os.path.join(ZIP_DIR, zip_name)
    with ZipFile(zip_path, 'w') as zipf:
        for file in file_paths:
            if os.path.exists(file):
                zipf.write(file, os.path.basename(file))
    return zip_path

