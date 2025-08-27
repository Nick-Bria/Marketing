import os
import re
import sys
import json
import argparse
from typing import Optional

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def extract_drive_file_id(shared_url: str) -> Optional[str]:
    """
    Extract the Google Drive file id from a typical share URL.
    Supported formats include:
      - https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing
      - https://drive.google.com/uc?id=<FILE_ID>
    """
    if not shared_url:
        return None

    # Match /file/d/<id>/
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)/", shared_url)
    if match:
        return match.group(1)

    # Match uc?id=<id>
    match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", shared_url)
    if match:
        return match.group(1)

    return None


def build_drive_direct_download_url(file_id: str) -> str:
    """Constructs a direct-download style URL for Google Drive file id."""
    return f"https://drive.google.com/uc?id={file_id}"


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(
            f"Environment variable {name} is not set.\n"
            f"Please set it, for example:\n\n"
            f"  export {name}=YOUR_TOKEN_HERE\n\n"
            f"Then re-run: python app.py"
        )
        sys.exit(2)
    return value


def call_bria_increase_resolution(
    api_token: str,
    video_field: str,
    desired_increase: int = 2,
    output_container_and_codec: str = "mp4_h265",
    timeout_seconds: int = 15,
) -> tuple[int, str]:
    url = "https://engine.prod.bria-api.com/v2/video/edit/increase_resolution"
    headers = {
        "Content-Type": "application/json",
        "api_token": api_token,
    }
    payload = {
        "video": video_field,
        "desired_increase": desired_increase,
        "output_container_and_codec": output_container_and_codec,
    }
    data = json.dumps(payload).encode("utf-8")

    request = Request(url=url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            body = response.read().decode("utf-8", errors="replace")
            return status, body
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except URLError as e:
        return 0, f"Network error: {e}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Increase video resolution via Bria using a Google Drive file link.")
    parser.add_argument(
        "--drive-url",
        default="https://drive.google.com/file/d/1hmKANy1-GRTLsomjl7qe-R2YoSIWGwFS/view?usp=sharing",
        help="Google Drive share URL of the input video (defaults to the provided link).",
    )
    parser.add_argument(
        "--desired-increase",
        type=int,
        default=2,
        help="Desired resolution increase factor (default: 2)",
    )
    parser.add_argument(
        "--codec",
        default="mp4_h265",
        help="Output container and codec string (default: mp4_h265)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="HTTP request timeout in seconds (default: 15)",
    )
    args = parser.parse_args()

    api_token = get_required_env("BRIA_API_TOKEN")

    file_id = extract_drive_file_id(args.drive_url)
    if not file_id:
        print("Could not extract Google Drive file id from the provided URL.")
        sys.exit(3)

    direct_url = build_drive_direct_download_url(file_id)
    print(f"Using Google Drive direct link as video field: {direct_url}")

    status_code, body = call_bria_increase_resolution(
        api_token=api_token,
        video_field=direct_url,
        desired_increase=args.desired_increase,
        output_container_and_codec=args.codec,
        timeout_seconds=args.timeout,
    )
    print(f"Status: {status_code}")
    # Try to pretty print JSON body if possible
    try:
        parsed = json.loads(body)
        print(json.dumps(parsed, indent=2))
    except Exception:
        print(body)


if __name__ == "__main__":
    main()

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
