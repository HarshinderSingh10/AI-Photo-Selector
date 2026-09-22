# AI Photo Selector

An AI-powered photo selection system that scans a large Google Drive photo collection, detects faces, generates face embeddings, and identifies photos containing a specific reference person.

The system is designed for large photo collections where manually searching through thousands of images would be time-consuming.

## 🚀 Project Overview

**AI Photo Selector** automates the process of finding photos of a specific person from a large collection of images.

The system uses **InsightFace / ArcFace face embeddings** to represent faces numerically and compares detected faces against a pre-built reference face profile.

### Pipeline

```text
Google Drive
     │
     ▼
Retrieve Image Thumbnails
     │
     ▼
Face Detection
     │
     ▼
Face Embedding Extraction
     │
     ▼
Compare with Reference Face
     │
     ▼
Similarity Score
     │
     ▼
Threshold Filtering
     │
     ▼
Selected Photos
```

## ✨ Features

* 🔍 Face detection from large image collections
* 🧠 Face recognition using deep face embeddings
* 📁 Google Drive photo collection scanning
* ⚡ Thumbnail-based image processing
* 🎯 Reference-person matching
* 📊 Similarity score calculation
* 💾 Persistent reference face profile
* 📈 Scan progress tracking
* 🧪 Thumbnail-resolution testing
* 🔄 Ability to resume long-running scans
* 🖼️ Stores selected images based on matching confidence

## 🧠 How It Works

### 1. Reference Face Profile

Reference images of the target person are processed using InsightFace.

The detected face is converted into a numerical embedding:

```text
Face Image
     ↓
Face Detection
     ↓
Face Alignment
     ↓
ArcFace Embedding
     ↓
512-dimensional vector
```

Multiple reference images can be used to create a more robust representation of the target person's appearance.

### 2. Google Drive Image Retrieval

The system connects to Google Drive and retrieves images from the selected photo collection.

Instead of downloading the original high-resolution files, the system can work with Google Drive thumbnails to reduce bandwidth and processing requirements.

### 3. Face Detection

Each image is analyzed for faces.

Images without detectable faces can be skipped, reducing unnecessary embedding computation.

### 4. Face Embeddings

Detected faces are converted into numerical representations using **InsightFace's ArcFace-based recognition model**.

The resulting embedding represents facial characteristics in a high-dimensional vector space.

### 5. Face Matching

The embedding from each detected face is compared with the reference profile.

A similarity score is calculated for every detected face.

Conceptually:

```text
Reference Embedding
        │
        │
        ├──── Similarity ────► Detected Face
        │
        ▼
   Match Score
```

If the score exceeds the configured matching threshold, the image is considered a potential match.

## 🛠️ Tech Stack

| Technology       | Purpose                        |
| ---------------- | ------------------------------ |
| Python           | Core application               |
| InsightFace      | Face detection and recognition |
| ArcFace          | Face embedding model           |
| OpenCV           | Image processing               |
| NumPy            | Numerical operations           |
| Google Drive API | Photo retrieval                |
| Pickle           | Reference profile persistence  |
| JSON             | Progress and result storage    |
| PyCharm          | Development environment        |
| Git & GitHub     | Version control                |

## 📁 Project Structure

```text
AI-Photo-Selector/
│
├── app.py
│
├── connection_test.py
│
├── drive_face_test.py
│
├── face_test.py
│
├── full_face_scan.py
│
├── reference_profile.py
│
├── thumbnail_test.py
│
├── thumbnail_resolution_test.py
│
├── .gitignore
│
└── README.md
```

### Main Components

**`app.py`**

Main application entry point.

**`connection_test.py`**

Used to verify connectivity and required external services.

**`drive_face_test.py`**

Tests face matching using images retrieved from Google Drive.

**`face_test.py`**

Used for local face detection and recognition testing.

**`full_face_scan.py`**

Performs the large-scale photo scanning and matching workflow.

**`reference_profile.py`**

Creates and manages the reference face profile used for matching.

**`thumbnail_test.py`**

Tests Google Drive thumbnail retrieval and image processing.

**`thumbnail_resolution_test.py`**

Evaluates different thumbnail resolutions for image analysis.

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/HarshinderSingh10/AI-Photo-Selector.git

c
```
