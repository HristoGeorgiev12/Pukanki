import os
import sys
import zipfile
import json
import glob

CONV_ID = "b8f68aca-f948-4f01-8f00-92ca57215eab"
BRAIN_DIR = os.path.expanduser(f"~/.gemini/antigravity/brain/{CONV_ID}")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".chat_session_backup")

os.makedirs(BACKUP_DIR, exist_ok=True)
zip_path = os.path.join(BACKUP_DIR, f"{CONV_ID}.zip")

print(f"Archiving conversation from: {BRAIN_DIR}")
if not os.path.exists(BRAIN_DIR):
    print(f"Error: Brain directory not found at {BRAIN_DIR}")
    sys.exit(1)

total_files = 0
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(BRAIN_DIR):
        if "browser_evidence" in root:
            continue
        for file in files:
            fp = os.path.join(root, file)
            arcname = os.path.relpath(fp, BRAIN_DIR)
            z.write(fp, arcname)
            total_files += 1

size_mb = os.path.getsize(zip_path) / (1024 * 1024)
print(f"Backup created successfully: {zip_path}")
print(f"Total files: {total_files}, Size: {size_mb:.2f} MB")
