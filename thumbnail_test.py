import json
import os
import requests

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


# ============================================================
# CONFIGURATION
# ============================================================

CATALOGUE_FILE = "photo_catalogue.json"
OUTPUT_FOLDER = "test_thumbnails"

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly"
]

NUMBER_OF_TEST_IMAGES = 10


# ============================================================
# LOAD GOOGLE CREDENTIALS
# ============================================================

def load_credentials():

    if not os.path.exists("token.json"):

        raise FileNotFoundError(
            "token.json was not found. "
            "Run app.py first to authenticate Google Drive."
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
# LOAD PHOTO CATALOGUE
# ============================================================

def load_catalogue():

    if not os.path.exists(CATALOGUE_FILE):

        raise FileNotFoundError(
            f"{CATALOGUE_FILE} was not found. "
            "Run app.py first."
        )

    with open(
        CATALOGUE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# DOWNLOAD THUMBNAIL
# ============================================================

def download_thumbnail(
    session,
    thumbnail_url,
    output_path
):

    response = session.get(
        thumbnail_url,
        timeout=30
    )

    response.raise_for_status()

    with open(
        output_path,
        "wb"
    ) as file:

        file.write(response.content)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("             THUMBNAIL TEST")
    print("=" * 60)

    # --------------------------------------------------------
    # Load catalogue
    # --------------------------------------------------------

    photos = load_catalogue()

    print(
        f"Images available in catalogue: {len(photos):,}"
    )

    # --------------------------------------------------------
    # Create output folder
    # --------------------------------------------------------

    os.makedirs(
        OUTPUT_FOLDER,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Load credentials
    # --------------------------------------------------------

    creds = load_credentials()

    print("Google credentials loaded.")

    # --------------------------------------------------------
    # Create authenticated HTTP session
    # --------------------------------------------------------

    session = requests.Session()

    session.headers.update({
        "Authorization": f"Bearer {creds.token}"
    })

    # --------------------------------------------------------
    # Select first 10 images that have thumbnails
    # --------------------------------------------------------

    selected = []

    for photo in photos:

        thumbnail_url = photo.get(
            "thumbnailLink"
        )

        if thumbnail_url:

            selected.append(photo)

        if len(selected) >= NUMBER_OF_TEST_IMAGES:

            break

    print(
        f"Images selected for test: {len(selected)}"
    )

    # --------------------------------------------------------
    # Download thumbnails
    # --------------------------------------------------------

    successful = 0
    failed = 0

    for index, photo in enumerate(
        selected,
        start=1
    ):

        name = photo["name"]

        thumbnail_url = photo.get(
            "thumbnailLink"
        )

        output_path = os.path.join(
            OUTPUT_FOLDER,
            f"{index:03d}.jpg"
        )

        print()
        print(
            f"[{index}/{len(selected)}] {name}"
        )

        try:

            download_thumbnail(
                session,
                thumbnail_url,
                output_path
            )

            successful += 1

            print(
                f"Saved → {output_path}"
            )

        except Exception as e:

            failed += 1

            print(
                f"FAILED: {e}"
            )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("THUMBNAIL TEST COMPLETE")
    print("=" * 60)

    print(
        f"Successful: {successful}"
    )

    print(
        f"Failed:     {failed}"
    )

    print(
        f"Output:     {OUTPUT_FOLDER}/"
    )

    print("=" * 60)


if __name__ == "__main__":

    main()