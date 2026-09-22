from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import json
import time


# ============================================================
# CONFIGURATION
# ============================================================

# Read-only access to Google Drive
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Your shared folder
ROOT_FOLDER_ID = "10DpHwhyJZ0dhE1xthdJdg_-2DEaNtr9e"
ROOT_FOLDER_NAME = "Rishav & Sakshi Photo"

# Local catalogue file
CATALOGUE_FILE = "photo_catalogue.json"


# Google Drive MIME types
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/x-icon",
    "image/avif",
}


# ============================================================
# GOOGLE DRIVE AUTHENTICATION
# ============================================================

def authenticate_google_drive():
    """
    Authenticate the user and return a Google Drive API service.
    """

    creds = None

    # --------------------------------------------------------
    # Check whether we already have a saved token
    # --------------------------------------------------------

    if os.path.exists("token.json"):

        print("Loading saved Google authentication...")

        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    # --------------------------------------------------------
    # If credentials don't exist or are invalid
    # --------------------------------------------------------

    if not creds or not creds.valid:

        # Try refreshing the existing token
        if creds and creds.expired and creds.refresh_token:

            print("Refreshing Google authentication...")

            creds.refresh(Request())

        else:

            print("Opening Google authentication...")

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        # ----------------------------------------------------
        # Save token for future use
        # ----------------------------------------------------

        with open("token.json", "w") as token:

            token.write(
                creds.to_json()
            )

        print("Google authentication saved.")

    print("Google authentication successful!")

    # --------------------------------------------------------
    # Create Google Drive API service
    # --------------------------------------------------------

    service = build(
        "drive",
        "v3",
        credentials=creds
    )

    return service


# ============================================================
# FIND SHARED FOLDER
# ============================================================

def find_shared_folder(service):
    """
    Find the main shared folder using its known ID.
    """

    print()
    print("=" * 70)
    print("CHECKING SHARED FOLDER")
    print("=" * 70)

    try:

        folder = service.files().get(
            fileId=ROOT_FOLDER_ID,
            fields=(
                "id,"
                "name,"
                "mimeType,"
                "size,"
                "parents,"
                "webViewLink"
            ),
            supportsAllDrives=True
        ).execute()

        print(f"Folder found: {folder['name']}")
        print(f"Folder ID: {folder['id']}")
        print(f"Folder type: {folder['mimeType']}")

        if folder["mimeType"] != FOLDER_MIME_TYPE:

            print()
            print("ERROR: The specified ID is not a folder.")

            return None

        return folder

    except Exception as e:

        print()
        print("Could not access the shared folder.")
        print(f"Error: {e}")

        return None


# ============================================================
# LIST CHILDREN OF A FOLDER
# ============================================================

def list_folder_contents(service, folder_id):
    """
    Return all files and folders directly inside a folder.

    Handles Google Drive pagination automatically.
    """

    all_items = []

    page_token = None

    while True:

        response = service.files().list(

            # Files whose parent is the current folder
            q=(
                f"'{folder_id}' in parents "
                f"and trashed = false"
            ),

            # Maximum allowed page size
            pageSize=1000,

            pageToken=page_token,

            spaces="drive",

            includeItemsFromAllDrives=True,

            supportsAllDrives=True,

            orderBy="name",

            fields=(
                "nextPageToken,"
                "files("
                "id,"
                "name,"
                "mimeType,"
                "size,"
                "parents,"
                "createdTime,"
                "modifiedTime,"
                "webViewLink,"
                "thumbnailLink,"
                "md5Checksum"
                ")"
            )

        ).execute()

        items = response.get("files", [])

        all_items.extend(items)

        page_token = response.get("nextPageToken")

        if not page_token:

            break

    return all_items


# ============================================================
# RECURSIVE DRIVE SCANNER
# ============================================================

def scan_folder(service, folder_id, folder_path, stats, image_catalogue):
    """
    Recursively scan a Google Drive folder.

    IMPORTANT:
    This function does NOT download any images.
    It only collects metadata.
    """

    try:

        items = list_folder_contents(
            service,
            folder_id
        )

    except Exception as e:

        print()
        print(f"ERROR scanning folder: {folder_path}")
        print(f"Error: {e}")

        stats["errors"] += 1

        return

    # --------------------------------------------------------
    # Process every item
    # --------------------------------------------------------

    for item in items:

        item_id = item["id"]

        item_name = item["name"]

        mime_type = item["mimeType"]

        current_path = os.path.join(
            folder_path,
            item_name
        )

        # ====================================================
        # FOLDER
        # ====================================================

        if mime_type == FOLDER_MIME_TYPE:

            stats["folders"] += 1

            print(
                f"[FOLDER] {current_path}"
            )

            # Recursively scan the folder
            scan_folder(
                service,
                item_id,
                current_path,
                stats,
                image_catalogue
            )

        # ====================================================
        # IMAGE
        # ====================================================

        elif mime_type in IMAGE_MIME_TYPES:

            stats["images"] += 1

            # Get file size
            size = int(
                item.get("size", 0)
            )

            stats["total_image_size"] += size

            # Save metadata
            image_data = {

                "id": item_id,

                "name": item_name,

                "mimeType": mime_type,

                "size": size,

                "path": current_path,

                "createdTime": item.get(
                    "createdTime"
                ),

                "modifiedTime": item.get(
                    "modifiedTime"
                ),

                "webViewLink": item.get(
                    "webViewLink"
                ),

                "thumbnailLink": item.get(
                    "thumbnailLink"
                ),

                "md5Checksum": item.get(
                    "md5Checksum"
                )
            }

            image_catalogue.append(
                image_data
            )

            # Print progress every 100 images
            if stats["images"] % 100 == 0:

                print(
                    f"[IMAGE] "
                    f"{stats['images']:,} images found"
                )

        # ====================================================
        # VIDEO
        # ====================================================

        elif mime_type.startswith("video/"):

            stats["videos"] += 1

        # ====================================================
        # OTHER FILE
        # ====================================================

        else:

            stats["other"] += 1


# ============================================================
# SAVE IMAGE CATALOGUE
# ============================================================

def save_catalogue(image_catalogue):
    """
    Save image metadata to a local JSON file.
    """

    print()
    print("Saving image catalogue...")

    with open(
        CATALOGUE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            image_catalogue,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Catalogue saved to: {CATALOGUE_FILE}"
    )


# ============================================================
# DISPLAY SCAN RESULTS
# ============================================================

def display_results(stats):

    print()
    print("=" * 70)
    print("SCAN COMPLETE")
    print("=" * 70)

    print(
        f"Folders found : {stats['folders']:,}"
    )

    print(
        f"Images found  : {stats['images']:,}"
    )

    print(
        f"Videos found  : {stats['videos']:,}"
    )

    print(
        f"Other files   : {stats['other']:,}"
    )

    print(
        f"Errors        : {stats['errors']:,}"
    )

    # --------------------------------------------------------
    # Convert image size to GB
    # --------------------------------------------------------

    image_size_gb = (
        stats["total_image_size"]
        / (1024 ** 3)
    )

    print(
        f"Image storage : {image_size_gb:.2f} GB"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    start_time = time.time()

    print()
    print("=" * 70)
    print("                    AI PHOTO SELECTOR")
    print("=" * 70)

    try:

        # ----------------------------------------------------
        # STEP 1
        # Authenticate
        # ----------------------------------------------------

        service = authenticate_google_drive()

        # ----------------------------------------------------
        # STEP 2
        # Check the shared folder
        # ----------------------------------------------------

        folder = find_shared_folder(
            service
        )

        if not folder:

            print()
            print(
                "Cannot continue because the shared "
                "folder could not be accessed."
            )

            return

        # ----------------------------------------------------
        # STEP 3
        # Initialize statistics
        # ----------------------------------------------------

        stats = {

            "folders": 0,

            "images": 0,

            "videos": 0,

            "other": 0,

            "errors": 0,

            "total_image_size": 0
        }

        # ----------------------------------------------------
        # STEP 4
        # Store image metadata
        # ----------------------------------------------------

        image_catalogue = []

        # ----------------------------------------------------
        # STEP 5
        # Scan entire folder
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print(
            f"STARTING SCAN: {ROOT_FOLDER_NAME}"
        )
        print("=" * 70)

        print()
        print(
            "IMPORTANT: No images will be downloaded."
        )

        print(
            "Only Google Drive metadata is being collected."
        )

        print()

        scan_folder(

            service,

            ROOT_FOLDER_ID,

            ROOT_FOLDER_NAME,

            stats,

            image_catalogue
        )

        # ----------------------------------------------------
        # STEP 6
        # Save catalogue
        # ----------------------------------------------------

        save_catalogue(
            image_catalogue
        )

        # ----------------------------------------------------
        # STEP 7
        # Display results
        # ----------------------------------------------------

        display_results(
            stats
        )

        # ----------------------------------------------------
        # Execution time
        # ----------------------------------------------------

        elapsed_time = (
            time.time() - start_time
        )

        print()
        print(
            f"Scan time: {elapsed_time:.2f} seconds"
        )

        print()
        print(
            "Your Google Drive has been successfully "
            "catalogued."
        )

    except KeyboardInterrupt:

        print()
        print(
            "Scan stopped by user."
        )

    except Exception as e:

        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)

        print(
            f"{type(e).__name__}: {e}"
        )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()