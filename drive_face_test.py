import os
import json
import pickle
import cv2
import requests
import numpy as np

from tqdm import tqdm
from insightface.app import FaceAnalysis
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# ============================================================
# SETTINGS
# ============================================================

CATALOGUE_FILE = "photo_catalogue.json"
PROFILE_FILE = "reference_profile.pkl"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

TEST_COUNT = 30
THUMBNAIL_SIZE = 1600

# Folder where test thumbnails will be saved
TEST_FOLDER = "drive_face_test"

os.makedirs(TEST_FOLDER, exist_ok=True)


# ============================================================
# LOAD GOOGLE DRIVE CONNECTION
# ============================================================

print("=" * 60)
print("GOOGLE DRIVE FACE TEST")
print("=" * 60)

creds = Credentials.from_authorized_user_file(
    "token.json",
    SCOPES
)

if creds.expired and creds.refresh_token:
    from google.auth.transport.requests import Request
    creds.refresh(Request())

service = build("drive", "v3", credentials=creds)

print("✅ Google Drive connected")


# ============================================================
# LOAD PHOTO CATALOGUE
# ============================================================

with open(CATALOGUE_FILE, "r", encoding="utf-8") as f:
    catalogue = json.load(f)

print(f"✅ Catalogue loaded")


# ============================================================
# FIND IMAGE RECORDS
# ============================================================

# The catalogue structure may contain folders/files in different
# formats, so recursively collect image records.

image_records = []


def collect_images(data):

    if isinstance(data, list):

        for item in data:
            collect_images(item)

    elif isinstance(data, dict):

        # If this looks like an image/file record
        mime_type = data.get("mimeType", "")

        if mime_type.startswith("image/") and data.get("id"):
            image_records.append(data)

        # Search nested values
        for value in data.values():

            if isinstance(value, (dict, list)):
                collect_images(value)


collect_images(catalogue)


# Remove duplicate IDs
unique_images = {}

for image in image_records:
    unique_images[image["id"]] = image

image_records = list(unique_images.values())

print(f"Images found in catalogue: {len(image_records)}")


if len(image_records) == 0:
    print("❌ No images found in catalogue.")
    exit()


# ============================================================
# SELECT 30 PHOTOS
# ============================================================

# Spread the test across the catalogue rather than taking
# the first 30 photos.

if len(image_records) <= TEST_COUNT:

    test_images = image_records

else:

    indexes = np.linspace(
        0,
        len(image_records) - 1,
        TEST_COUNT,
        dtype=int
    )

    test_images = [image_records[i] for i in indexes]


print(f"Testing {len(test_images)} photos")


# ============================================================
# LOAD INSIGHTFACE
# ============================================================

print()
print("Loading InsightFace...")

app = FaceAnalysis(name="buffalo_l")

app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("✅ InsightFace ready")


# ============================================================
# LOAD REFERENCE PROFILE
# ============================================================

with open(PROFILE_FILE, "rb") as f:
    reference_profile = pickle.load(f)

reference_profile = np.asarray(
    reference_profile,
    dtype=np.float32
)

# Make absolutely sure it is normalized
reference_profile = (
    reference_profile /
    np.linalg.norm(reference_profile)
)

print("✅ Reference profile loaded")
print(f"Profile shape: {reference_profile.shape}")


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(a, b):

    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)

    if a_norm == 0 or b_norm == 0:
        return 0.0

    return float(
        np.dot(a, b) /
        (a_norm * b_norm)
    )


# ============================================================
# PROCESS PHOTOS
# ============================================================

results = []


print()
print("=" * 60)
print("PROCESSING TEST PHOTOS")
print("=" * 60)


for number, photo in enumerate(
    tqdm(test_images),
    start=1
):

    file_id = photo["id"]
    filename = photo.get(
        "name",
        f"{file_id}.jpg"
    )

    try:

        # ----------------------------------------------------
        # Get latest file metadata
        # ----------------------------------------------------

        metadata = service.files().get(
            fileId=file_id,
            fields="id,name,mimeType,thumbnailLink",
            supportsAllDrives=True
        ).execute()

        thumbnail_url = metadata.get("thumbnailLink")

        if not thumbnail_url:
            results.append({
                "filename": filename,
                "file_id": file_id,
                "faces": 0,
                "best_score": None,
                "error": "No thumbnail available"
            })
            continue

        # ----------------------------------------------------
        # Request larger thumbnail
        # ----------------------------------------------------

        thumbnail_url = thumbnail_url.split("=")[0]

        thumbnail_url += f"=s{THUMBNAIL_SIZE}"

        response = requests.get(
            thumbnail_url,
            timeout=30
        )

        response.raise_for_status()

        image_bytes = np.frombuffer(
            response.content,
            dtype=np.uint8
        )

        image = cv2.imdecode(
            image_bytes,
            cv2.IMREAD_COLOR
        )

        if image is None:

            results.append({
                "filename": filename,
                "file_id": file_id,
                "faces": 0,
                "best_score": None,
                "error": "Could not decode image"
            })

            continue

        # ----------------------------------------------------
        # Save test thumbnail
        # ----------------------------------------------------

        safe_name = (
            f"{number:02d}_" +
            filename.replace("/", "_")
        )

        save_path = os.path.join(
            TEST_FOLDER,
            safe_name
        )

        cv2.imwrite(
            save_path,
            image
        )

        # ----------------------------------------------------
        # Detect faces
        # ----------------------------------------------------

        faces = app.get(image)

        scores = []

        for face in faces:

            score = cosine_similarity(
                face.embedding,
                reference_profile
            )

            scores.append(score)

        # ----------------------------------------------------
        # Best match
        # ----------------------------------------------------

        if scores:

            best_score = max(scores)

        else:

            best_score = None

        results.append({
            "filename": filename,
            "file_id": file_id,
            "faces": len(faces),
            "best_score": best_score,
            "all_scores": scores,
            "error": None
        })

    except Exception as e:

        results.append({
            "filename": filename,
            "file_id": file_id,
            "faces": 0,
            "best_score": None,
            "error": str(e)
        })


# ============================================================
# SAVE RESULTS
# ============================================================

RESULTS_FILE = "drive_face_test_results.json"

with open(
    RESULTS_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        results,
        f,
        indent=2
    )


# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print()
print("=" * 80)
print("FACE MATCH RESULTS")
print("=" * 80)

for i, result in enumerate(results, start=1):

    filename = result["filename"]
    faces = result["faces"]
    score = result["best_score"]
    error = result["error"]

    if error:

        print(
            f"{i:02d}. {filename}"
            f" | ERROR: {error}"
        )

    elif score is None:

        print(
            f"{i:02d}. {filename}"
            f" | Faces: {faces}"
            f" | Best score: NO FACE"
        )

    else:

        print(
            f"{i:02d}. {filename}"
            f" | Faces: {faces}"
            f" | Best score: {score:.4f}"
        )


# ============================================================
# SUMMARY
# ============================================================

valid_scores = [
    r["best_score"]
    for r in results
    if r["best_score"] is not None
]

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"Photos tested       : {len(results)}")
print(f"Photos with faces   : {len(valid_scores)}")
print(
    f"Photos without face : "
    f"{len(results) - len(valid_scores)}"
)

if valid_scores:

    print(
        f"Highest score      : "
        f"{max(valid_scores):.4f}"
    )

    print(
        f"Lowest score       : "
        f"{min(valid_scores):.4f}"
    )

    print(
        f"Average score      : "
        f"{np.mean(valid_scores):.4f}"
    )

print()
print(f"Test thumbnails saved to: {TEST_FOLDER}")
print(f"Results saved to: {RESULTS_FILE}")

print()
print("✅ TEST COMPLETE")