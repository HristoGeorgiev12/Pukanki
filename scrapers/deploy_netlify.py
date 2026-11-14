import io
import json
import os
import sys
import time
import urllib.request
import zipfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env_vars() -> dict[str, str]:
    env = {}
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip("'\"")
    return env


_local_env = load_env_vars()
SITE_ID = os.environ.get("NETLIFY_SITE_ID", _local_env.get("NETLIFY_SITE_ID", "c9c908c8-4cc3-489f-91d7-6faa0ad31e62"))
TOKEN = os.environ.get("NETLIFY_TOKEN", _local_env.get("NETLIFY_TOKEN", ""))


def build_deploy_zip() -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. index.html & favicon.svg
        for root_file in ["index.html", "favicon.svg"]:
            p = os.path.join(BASE_DIR, root_file)
            if os.path.exists(p):
                zip_file.write(p, arcname=root_file)
                print(f"[+] Added {root_file} ({os.path.getsize(p) / 1024:.1f} KB)")

        # 2. data/*.js files (and optionally .json if needed)
        data_dir = os.path.join(BASE_DIR, "data")
        for fname in os.listdir(data_dir):
            if fname.endswith("_data.js"):
                fp = os.path.join(data_dir, fname)
                arc = f"data/{fname}"
                zip_file.write(fp, arcname=arc)
                print(f"[+] Added {arc} ({os.path.getsize(fp) / (1024 * 1024):.2f} MB)")

    zip_bytes = zip_buffer.getvalue()
    print(f"[*] Total zip size: {len(zip_bytes) / (1024 * 1024):.2f} MB")
    return zip_bytes


def deploy_to_netlify(zip_bytes: bytes):
    url = f"https://api.netlify.com/api/v1/sites/{SITE_ID}/deploys"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/zip",
        "User-Agent": "PukankiDeployer/1.0",
    }

    print(f"[*] Uploading deploy zip to Netlify site {SITE_ID}...")
    req = urllib.request.Request(url, data=zip_bytes, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            deploy_id = data.get("id")
            state = data.get("state")
            deploy_url = data.get("deploy_url")
            ssl_url = data.get("ssl_url")
            print(f"[SUCCESS] Deploy submitted!")
            print(f"Deploy ID: {deploy_id}")
            print(f"State: {state}")
            print(f"Deploy URL: {deploy_url}")
            print(f"Live URL: {ssl_url}")
            return data
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP Error {e.code}: {e.read().decode('utf-8', 'ignore')}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Deploy failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    zip_data = build_deploy_zip()
    deploy_to_netlify(zip_data)

