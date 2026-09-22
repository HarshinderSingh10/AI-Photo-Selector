import json
import os
import re

import requests
from PIL import Image
from io import BytesIO

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


# ============================================================
# CONFIGURATION
# ============================================================

CATALOGUE_FILE = "photo_catalogue.json"
OUTPUT_FOLDER = "resolution_test"

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly"
]

# Resolutions we want to test
TEST_SIZES = [
    220,
    800,
    1600,
    2000
]


# ============================================================
# LOAD GOOGLE CREDENTIALS
# ============================================================

def load_credentials():

    if not os.path.exists("token.json"):

        raise FileNotFoundError(
            "token.json not found. "
            "Run app.py first."
        )

    creds = Credentials.from_authorized_user_file(
        "token.json",
        SCOPES
    )

    if creds.expired and creds.refresh_token:

        print("Refreshing Google authentication...")

        creds.refresh(Request())

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


# ============================================================
# LOAD CATALOGUE
# ============================================================

def load_catalogue():

    if not os.path.exists(CATALOGUE_FILE):

        raise FileNotFoundError(
            f"{CATALOGUE_FILE} not found."
        )

    with open(
        CATALOGUE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# MODIFY THUMBNAIL URL
# ============================================================

def change_thumbnail_size(url, size):
    """
    Attempt to change Google's thumbnail size parameter.

    Example:

        ...=s220

    becomes:

        ...=s1600
    """

    # Common format: =s220
    modified = re.sub(
        r"=s\d+$",
        f"=s{size}",
        url
    )

    # Some URLs may have additional parameters after s220.
    if modified == url:

        modified = re.sub(
            r"=s\d+(&.*)?$",
            lambda match:
                f"=s{size}" + (
                    match.group(1)
                    if match.group(1)
                    else ""
                ),
            url
        )

    return modified


# ============================================================
# DOWNLOAD IMAGE
# ============================================================

def download_image(
    session,
    url
):

    response = session.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    return response.content


# ============================================================
# ANALYSE IMAGE
# ============================================================

def analyse_image(data):

    image = Image.open(
        BytesIO(data)
    )

    return {
        "width": image.width,
        "height": image.height,
        "format": image.format,
        "size_bytes": len(data)
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("           GOOGLE DRIVE THUMBNAIL RESOLUTION TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # Load catalogue
    # --------------------------------------------------------

    photos = load_catalogue()

    # Find first image with thumbnail URL
    photo = None

    for item in photos:

        if item.get("thumbnailLink"):

            photo = item
            break

    if not photo:

        print("No image with a thumbnailLink was found.")

        return

    print()
    print("TEST IMAGE")
    print("-" * 70)

    print(f"Name: {photo['name']}")
    print(f"File ID: {photo['id']}")
    print(f"Original size: {photo.get('size', 'Unknown')} bytes")

    original_thumbnail_url = photo["thumbnailLink"]

    print()
    print("Original thumbnail URL:")
    print(original_thumbnail_url)

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Load credentials
    # --------------------------------------------------------

    creds = load_credentials()

    session = requests.Session()

    session.headers.update({
        "Authorization": f"Bearer {creds.token}"
    })

    # --------------------------------------------------------
    # Test different resolutions
    # --------------------------------------------------------

    results = []

    for size in TEST_SIZES:

        print()
        print("-" * 70)
        print(f"Testing requested size: s{size}")
        print("-" * 70)

        test_url = change_thumbnail_size(
            original_thumbnail_url,
            size
        )

        print(f"URL: {test_url}")

        try:

            data = download_image(
                session,
                test_url
            )

            info = analyse_image(
                data
            )

            output_path = os.path.join(
                OUTPUT_FOLDER,
                f"test_s{size}.jpg"
            )

            with open(
                output_path,
                "wb"
            ) as file:

                file.write(data)

            result = {
                "requested_size": size,
                "actual_width": info["width"],
                "actual_height": info["height"],
                "format": info["format"],
                "downloaded_bytes": info["size_bytes"],
                "path": output_path
            }

            results.append(result)

            print(
                f"Actual resolution: "
                f"{info['width']} × {info['height']}"
            )

            print(
                f"Downloaded size: "
                f"{info['size_bytes'] / 1024:.2f} KB"
            )

            print(
                f"Saved: {output_path}"
            )

        except Exception as e:

            print(
                f"FAILED: {type(e).__name__}: {e}"
            )

    # --------------------------------------------------------
    # Final comparison
    # --------------------------------------------------------

    print()
    print()
    print("=" * 70)
    print("                     RESULTS")
    print("=" * 70)

    print(
        f"{'Requested':<12}"
        f"{'Actual':<20}"
        f"{'Size':<15}"
    )

    print("-" * 70)

    for result in results:

        actual = (
            f"{result['actual_width']} × "
            f"{result['actual_height']}"
        )

        downloaded = (
            f"{result['downloaded_bytes'] / 1024:.2f} KB"
        )

        print(
            f"s{result['requested_size']:<10}"
            f"{actual:<20}"
            f"{downloaded:<15}"
        )

    print("=" * 70)

    # --------------------------------------------------------
    # Interpretation
    # --------------------------------------------------------

    if len(results) >= 2:

        first = results[0]

        larger_results = [
            r for r in results
            if r["actual_width"] > first["actual_width"]
        ]

        print()

        if larger_results:

            print(
                "SUCCESS: Google returned higher-resolution "
                "images for larger size requests."
            )

            print()
            print(
                "This means we may be able to use a larger "
                "preview for face recognition without "
                "downloading the original files."
            )

        else:

            print(
                "No resolution increase was detected."
            )

            print()
            print(
                "Changing the size parameter does not appear "
                "to provide a larger image for this file."
            )


if __name__ == "__main__":

    main()