import os
import cv2
import numpy as np
import pickle
from insightface.app import FaceAnalysis

REFERENCE_FOLDER = "reference_faces"
OUTPUT_FILE = "reference_profile.pkl"

print("=" * 60)
print("BUILDING REFERENCE FACE PROFILE")
print("=" * 60)

# ---------------------------------------------------------
# Load InsightFace
# ---------------------------------------------------------

app = FaceAnalysis(name="buffalo_l")
app.prepare(ctx_id=0, det_size=(640, 640))

embeddings = []
processed = 0
failed = 0

# ---------------------------------------------------------
# Process reference images
# ---------------------------------------------------------

for filename in sorted(os.listdir(REFERENCE_FOLDER)):

    path = os.path.join(REFERENCE_FOLDER, filename)

    if not filename.lower().endswith(
        (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".heif")
    ):
        continue

    image = cv2.imread(path)

    if image is None:
        print(f"❌ Could not read: {filename}")
        failed += 1
        continue

    faces = app.get(image)

    if len(faces) != 1:
        print(f"❌ Expected 1 face, found {len(faces)}: {filename}")
        failed += 1
        continue

    embedding = faces[0].embedding.astype(np.float32)

    # Normalize individual embedding
    embedding = embedding / np.linalg.norm(embedding)

    embeddings.append(embedding)
    processed += 1

    print(f"✅ {filename}")

# ---------------------------------------------------------
# Check results
# ---------------------------------------------------------

print()
print("=" * 60)
print("REFERENCE PROCESSING COMPLETE")
print("=" * 60)

print(f"Reference images processed : {processed}")
print(f"Failed images              : {failed}")

if len(embeddings) == 0:
    print("\n❌ No valid reference embeddings found.")
    exit()

# ---------------------------------------------------------
# Create identity centroid
# ---------------------------------------------------------

embeddings = np.array(embeddings, dtype=np.float32)

print(f"\nEmbedding matrix shape: {embeddings.shape}")

# Average all reference embeddings
profile = np.mean(embeddings, axis=0)

# Normalize final profile
profile = profile / np.linalg.norm(profile)

print(f"Identity profile shape: {profile.shape}")

# ---------------------------------------------------------
# Save profile
# ---------------------------------------------------------

with open(OUTPUT_FILE, "wb") as f:
    pickle.dump(profile, f)

print()
print("=" * 60)
print("IDENTITY PROFILE CREATED")
print("=" * 60)

print(f"Saved to: {OUTPUT_FILE}")
print("Profile dimension: 512")
print(f"Based on {len(embeddings)} reference images")

print()
print("✅ Your reference profile is ready.")