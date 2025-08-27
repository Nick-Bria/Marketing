import os
import sys
import json
import subprocess
import shutil
from pathlib import Path

import requests

GOOGLE_DRIVE_FILE_ID = "1hmKANy1-GRTLsomjl7qe-R2YoSIWGwFS"
DOWNLOAD_URL = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
OUTPUT_VIDEO = Path("video.mp4")
BRIA_API_URL = "https://engine.prod.bria-api.com/v2/video/edit/increase_resolution"


def ensure_dependency(package: str) -> None:
    try:
        __import__(package)
    except ImportError:
        print(f"Installing missing dependency: {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def download_from_google_drive(url: str, output_path: Path) -> None:
    ensure_dependency("gdown")
    import gdown
    print(f"Downloading file from Google Drive to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdown.download(url, str(output_path), quiet=False)
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Download failed or produced empty file")


def call_bria_increase_resolution(video_reference: str, desired_increase: int = 2, output_codec: str = "mp4_h265") -> requests.Response:
    api_token = os.getenv("BRIA_API_TOKEN")
    if not api_token:
        raise RuntimeError("Environment variable BRIA_API_TOKEN is not set. Export it before running.")

    headers = {
        "Content-Type": "application/json",
        "api_token": api_token,
    }
    payload = {
        "video": video_reference,
        "desired_increase": desired_increase,
        "output_container_and_codec": output_codec,
    }
    print("Calling Bria API...")
    response = requests.post(BRIA_API_URL, headers=headers, data=json.dumps(payload), timeout=120)
    return response


def main() -> int:
    try:
        # Step 1: Download the sample video
        download_from_google_drive(DOWNLOAD_URL, OUTPUT_VIDEO)

        # Step 2: Provide the path or URL as Bria expects. Many APIs expect a URL; if local paths are not supported,
        # the call might fail. Well
