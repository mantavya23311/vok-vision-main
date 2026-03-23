# VokVision: Professional 3D AI Reconstruction Engine 

VokVision is an elite-grade 3D reconstruction platform that transforms a handful of 2D images into high-fidelity 3D Gaussian Splats. Engineered for professional workflows, it utilizes a state-of-the-art hybrid AI pipeline to deliver industrial-standard results.

---

## "Elite Hybrid" Architecture

Unlike basic reconstruction scripts, VokVision uses a **Dual-Stage Hybrid Mapping** strategy:

1.  **VLM Image Audit**: Gemini 1.5 Flash filters out blurry or poorly lit images before processing begins.
2.  **Hybrid Mapping (SfM)**: Uses original images (with background) for perfect camera triangulation, ensuring 100% stable poses.
3.  **Surgical Point-Cloud Masking**: Automatically deletes background points using AI segmentation masks before training starts.
4.  **Gaussian Splatting (30K)**: Trained on **white-background** datasets with 30,000 iterations for a clean, professional, floater-free 3D object.

---

##  Windows / NVIDIA (RTX 4090) Setup Guide

This engine is optimized for high-end NVIDIA hardware. Follow these steps to achieve **10-minute professional scans.**

### 1. Prerequisites
- **CUDA Toolkit**: Install [CUDA 11.8 or 12.1](https://developer.nvidia.com/cuda-downloads).
- **Python 3.10+**: Ensure `pip` is updated.
- **Node.js**: For the orchestration API.

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/AbhigyanRaj/VokVision.git
cd VokVision/backend/processor

# Create Virtual Environment
python -m venv venv
source venv/Scripts/activate  # Windows

# Install Requirements
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### 3. "Elite" Configuration (`config.py`)
Ensure your `backend/processor/config.py` is set for GPU power:
```python
DEVICE = "cuda"       # Set to "cuda" for NVIDIA GPUs
ITERATIONS = 30000    # Professional standard (Higher = Better detail)
```

### 4. Running the Engine
1.  **Start Backend**: `cd backend/api && npm run dev`
2.  **Start Processor**: `cd backend/processor && python main.py`
3.  **Start Mobile**: Run the Flutter app on your device.

---

## Directory Structure

```plaintext
VokVision/
├── apps/mobile_app/        # Flutter Client
├── backend/api/            # Node.js Orchestrator (Job handling/Notifications)
├── backend/processor/      # Python AI Engine (MASt3R, OpenSplat, VLM)
├── pipeline/               # Core AI Modules (Submodules)
└── storage/                # Local data (Ignored by Git)
```

---

## Important Note on Checkpoints

The **MASt3R** model checkpoint (`MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth`) is required for the SfM stage. 
- Due to its size (>1GB), it is not included in the repository.
- It will automatically download on the first run, or you can place it manually in `pipeline/mast3r/`.

---

> [!TIP]
> **Pro Tip**: Use 20–40 images with 360-degree coverage and a clear "top-down" angle for the best 3D volume.
