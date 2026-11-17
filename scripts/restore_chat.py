import os
import sys
import zipfile

CONV_ID = "b8f68aca-f948-4f01-8f00-92ca57215eab"
TARGET_DIR = os.path.expanduser(f"~/.gemini/antigravity/brain/{CONV_ID}")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".chat_session_backup")
ZIP_PATH = os.path.join(BACKUP_DIR, f"{CONV_ID}.zip")

print("=== Възстановяване на Antigravity чат сесия ===")
if not os.path.exists(ZIP_PATH):
    print(f"Грешка: Архивът {ZIP_PATH} не е намерен!")
    sys.exit(1)

os.makedirs(TARGET_DIR, exist_ok=True)
print(f"Разархивиране към: {TARGET_DIR} ...")

with zipfile.ZipFile(ZIP_PATH, "r") as z:
    z.extractall(TARGET_DIR)

print("Успешно възстановена чат сесия!")
print(f"Чат ID: {CONV_ID}")
print("Сега можете да отворите Antigravity и да продължите разговора от списъка с чатове.")
