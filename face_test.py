import os
import cv2
from insightface.app import FaceAnalysis

REFERENCE_FOLDER = "reference_faces"

print("=" * 60)
print("REFERENCE FACE TEST")
print("=" * 60)

# Load InsightFace
app = FaceAnalysis(name="buffalo_l")
app.prepare(ctx_id=0, det_size=(640, 640))

reference_embeddings = []

for filename in os.listdir(REFERENCE_FOLDER):

    path = os.path.join(REFERENCE_FOLDER, filename)

    # Ignore non-image files
    if not filename.lower().endswith(
        (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".heif")
    ):
        continue

    # Load image into OpenCV/Numpy array
    image = cv2.imread(path)

    if image is None:
        print(f"❌ Could not read: {filename}")
        continue

    # Detect faces
    faces = app.get(image)

    if len(faces) == 0:
        print(f"❌ No face detected: {filename}")
        continue

    # Use the largest detected face
    face = max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) *
                      (f.bbox[3] - f.bbox[1])
    )

    reference_embeddings.append(face.embedding)

    print(f"✅ {filename}")
    print(f"   Faces detected: {len(faces)}")
    print(f"   Embedding shape: {face.embedding.shape}")

print()
print("=" * 60)
print(f"Reference faces loaded: {len(reference_embeddings)}")
print("=" * 60)