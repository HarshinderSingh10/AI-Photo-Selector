import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly"
]

ROOT_FOLDER_ID = "10DpHwhyJZ0dhE1xthdJdg_-2DEaNtr9e"


def main():

    print("=" * 60)
    print("           AI PHOTO SELECTOR")
    print("           CONNECTION TEST")
    print("=" * 60)

    # --------------------------------------------------------
    # Check token
    # --------------------------------------------------------

    if not os.path.exists("token.json"):

        print("\n❌ token.json not found.")
        print("Run app.py first to authenticate.")

        return

    try:

        # ----------------------------------------------------
        # Load credentials
        # ----------------------------------------------------

        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

        # ----------------------------------------------------
        # Refresh if necessary
        # ----------------------------------------------------

        if creds.expired and creds.refresh_token:

            print("\nRefreshing Google authentication...")

            creds.refresh(Request())

            with open("token.json", "w") as token:

                token.write(
                    creds.to_json()
                )

        # ----------------------------------------------------
        # Build Drive service
        # ----------------------------------------------------

        service = build(
            "drive",
            "v3",
            credentials=creds
        )

        print("\n✅ Google authentication: OK")

        # ----------------------------------------------------
        # Check the actual shared folder
        # ----------------------------------------------------

        folder = service.files().get(

            fileId=ROOT_FOLDER_ID,

            fields=(
                "id,"
                "name,"
                "mimeType"
            ),

            supportsAllDrives=True

        ).execute()

        print("✅ Google Drive API: OK")

        print(
            f"✅ Shared folder: {folder['name']}"
        )

        print(
            f"✅ Folder ID: {folder['id']}"
        )

        print()
        print("=" * 60)
        print("             CONNECTION IS WORKING")
        print("=" * 60)

    except Exception as e:

        print()
        print("=" * 60)
        print("❌ CONNECTION FAILED")
        print("=" * 60)

        print(
            f"{type(e).__name__}: {e}"
        )


if __name__ == "__main__":

    main()