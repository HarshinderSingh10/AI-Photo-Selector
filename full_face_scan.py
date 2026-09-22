import os
import json
import pickle
import cv2
import requests
import numpy as np
import time

from tqdm import tqdm
from insightface.app import FaceAnalysis
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# ============================================================
# SETTINGS
# ============================================================

CATALOGUE_FILE = "photo_catalogue.json"
PROFILE_FILE = "reference_profile.pkl"

RESULTS_FILE = "face_scan_results.json"
PROGRESS_FILE = "face_scan_progress.json"

THUMBNAIL_FOLDER = "face_scan_thumbnails"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

THUMBNAIL_SIZE = 1600

# Candidate threshold
THRESHOLD = 0.40

# Save thumbnails of candidates only
SAVE_CANDIDATE_THUMBNAILS = True

os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def cosine_similarity(a, b):

    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)

    if a_norm == 0 or b_norm == 0:
        return 0.0

    return float(np.dot(a, b) / (a_norm * b_norm))


def save_json(filename, data):

    temp_file = filename + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    os.replace(temp_file, filename)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("FULL GOOGLE DRIVE FACE SCAN")
print("=" * 70)

print(f"Thumbnail size : s{THUMBNAIL_SIZE}")
print(f"Match threshold: {THRESHOLD}")
print()


# ============================================================
# GOOGLE DRIVE CONNECTION
# ============================================================

print("Connecting to Google Drive...")

creds = Credentials.from_authorized_user_file(
    "token.json",
    SCOPES
)

if creds.expired and creds.refresh_token:

    from google.auth.transport.requests import Request

    creds.refresh(Request())

service = build(
    "drive",
    "v3",
    credentials=creds
)

print("✅ Google Drive connected")


# ============================================================
# LOAD CATALOGUE
# ============================================================

print("Loading photo catalogue...")

with open(
    CATALOGUE_FILE,
    "r",
    encoding="utf-8"
) as f:

    catalogue = json.load(f)


image_records = []


def collect_images(data):

    if isinstance(data, list):

        for item in data:
            collect_images(item)

    elif isinstance(data, dict):

        mime_type = data.get(
            "mimeType",
            ""
        )

        if (
            mime_type.startswith("image/")
            and data.get("id")
        ):

            image_records.append(data)

        for value in data.values():

            if isinstance(
                value,
                (dict, list)
            ):

                collect_images(value)


collect_images(catalogue)


# Remove duplicate files
unique_images = {}

for image in image_records:

    unique_images[image["id"]] = image


image_records = list(
    unique_images.values()
)

total_images = len(image_records)

print(
    f"✅ Images found: {total_images}"
)


# ============================================================
# LOAD REFERENCE PROFILE
# ============================================================

print("Loading reference profile...")

with open(
    PROFILE_FILE,
    "rb"
) as f:

    reference_profile = pickle.load(f)


reference_profile = np.asarray(
    reference_profile,
    dtype=np.float32
)

reference_profile = (
    reference_profile /
    np.linalg.norm(reference_profile)
)

print(
    f"✅ Reference profile loaded: "
    f"{reference_profile.shape}"
)


# ============================================================
# LOAD INSIGHTFACE
# ============================================================

print("Loading InsightFace...")

app = FaceAnalysis(
    name="buffalo_l"
)

app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("✅ InsightFace ready")
print()


# ============================================================
# LOAD PREVIOUS PROGRESS
# ============================================================

processed_ids = set()
results = []

if os.path.exists(PROGRESS_FILE):

    print("Previous progress found.")

    try:

        with open(
            PROGRESS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            progress = json.load(f)

        processed_ids = set(
            progress.get(
                "processed_ids",
                []
            )
        )

        results = progress.get(
            "results",
            []
        )

        print(
            f"✅ Resuming from "
            f"{len(processed_ids)} processed photos"
        )

    except Exception as e:

        print(
            f"⚠️ Could not load progress: {e}"
        )

        processed_ids = set()
        results = []

else:

    print("Starting new scan.")


# ============================================================
# SCAN
# ============================================================

remaining = [
    image
    for image in image_records
    if image["id"] not in processed_ids
]


print()
print("=" * 70)
print("STARTING SCAN")
print("=" * 70)

print(
    f"Total photos     : {total_images}"
)

print(
    f"Already processed: {len(processed_ids)}"
)

print(
    f"Remaining        : {len(remaining)}"
)

print()


start_time = time.time()


# ============================================================
# PROCESS EACH IMAGE
# ============================================================

for counter, photo in enumerate(
    tqdm(
        remaining,
        desc="Scanning photos"
    ),
    start=1
):

    file_id = photo["id"]

    filename = photo.get(
        "name",
        f"{file_id}.jpg"
    )

    result = {
        "file_id": file_id,
        "filename": filename,
        "faces": 0,
        "best_score": None,
        "matched": False,
        "thumbnail_path": None,
        "error": None
    }

    try:

        # ----------------------------------------------------
        # Get thumbnail URL
        # ----------------------------------------------------

        metadata = service.files().get(
            fileId=file_id,
            fields="id,name,mimeType,thumbnailLink",
            supportsAllDrives=True
        ).execute()

        thumbnail_url = metadata.get(
            "thumbnailLink"
        )

        if not thumbnail_url:

            result["error"] = (
                "No thumbnail available"
            )

            results.append(result)
            processed_ids.add(file_id)

            continue

        # ----------------------------------------------------
        # Request s1600 thumbnail
        # ----------------------------------------------------

        thumbnail_url = (
            thumbnail_url.split("=")[0]
            + f"=s{THUMBNAIL_SIZE}"
        )

        response = requests.get(
            thumbnail_url,
            timeout=60
        )

        response.raise_for_status()

        # ----------------------------------------------------
        # Decode image
        # ----------------------------------------------------

        image_bytes = np.frombuffer(
            response.content,
            dtype=np.uint8
        )

        image = cv2.imdecode(
            image_bytes,
            cv2.IMREAD_COLOR
        )

        if image is None:

            result["error"] = (
                "Could not decode thumbnail"
            )

            results.append(result)
            processed_ids.add(file_id)

            continue

        # ----------------------------------------------------
        # Detect faces
        # ----------------------------------------------------

        faces = app.get(image)

        result["faces"] = len(faces)

        best_score = -1.0
        best_face = None

        # ----------------------------------------------------
        # Compare every face
        # ----------------------------------------------------

        for face in faces:

            score = cosine_similarity(
                face.embedding,
                reference_profile
            )

            if score > best_score:

                best_score = score
                best_face = face

        # ----------------------------------------------------
        # Store best score
        # ----------------------------------------------------

        if best_face is not None:

            result["best_score"] = round(
                best_score,
                5
            )

            if best_score >= THRESHOLD:

                result["matched"] = True

                # --------------------------------------------
                # Save candidate thumbnail
                # --------------------------------------------

                if SAVE_CANDIDATE_THUMBNAILS:

                    safe_filename = (
                        filename
                        .replace("/", "_")
                        .replace("\\", "_")
                        .replace(":", "_")
                    )

                    thumbnail_path = os.path.join(
                        THUMBNAIL_FOLDER,
                        f"{best_score:.4f}_{safe_filename}"
                    )

                    cv2.imwrite(
                        thumbnail_path,
                        image
                    )

                    result[
                        "thumbnail_path"
                    ] = thumbnail_path

        # ----------------------------------------------------
        # Add result
        # ----------------------------------------------------

        results.append(result)
        processed_ids.add(file_id)

    except Exception as e:

        result["error"] = str(e)

        results.append(result)
        processed_ids.add(file_id)

    # --------------------------------------------------------
    # Save progress every 10 photos
    # --------------------------------------------------------

    if counter % 10 == 0:

        save_json(
            PROGRESS_FILE,
            {
                "processed_ids": list(
                    processed_ids
                ),
                "results": results
            }
        )


# ============================================================
# FINAL SAVE
# ============================================================

save_json(
    PROGRESS_FILE,
    {
        "processed_ids": list(
            processed_ids
        ),
        "results": results
    }
)

save_json(
    RESULTS_FILE,
    results
)


# ============================================================
# SUMMARY
# ============================================================

elapsed = time.time() - start_time

matched = [
    r for r in results
    if r["matched"]
]

with_faces = [
    r for r in results
    if r["faces"] > 0
]

errors = [
    r for r in results
    if r["error"] is not None
]


print()
print()
print("=" * 70)
print("SCAN COMPLETE")
print("=" * 70)

print(
    f"Photos processed : {len(results)}"
)

print(
    f"Photos with faces: {len(with_faces)}"
)

print(
    f"Candidate matches: {len(matched)}"
)

print(
    f"Errors           : {len(errors)}"
)

print(
    f"Time taken       : {elapsed / 60:.2f} minutes"
)

print()
print(
    f"Results saved to : {RESULTS_FILE}"
)

print(
    f"Progress saved to: {PROGRESS_FILE}"
)

print(
    f"Thumbnails saved : {THUMBNAIL_FOLDER}"
)

print()
print("✅ FULL SCAN FINISHED")