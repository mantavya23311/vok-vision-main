# VokVision: Professional 3D AI Reconstruction Engine

VokVision is an elite-grade 3D reconstruction platform that transforms a handful of 2D images into high-fidelity 3D Gaussian Splats. Engineered for professional workflows, it utilizes a state-of-the-art hybrid AI pipeline to deliver industrial-standard results.

---

## Elite Hybrid Architecture

Unlike basic reconstruction scripts, VokVision uses a Dual-Stage Hybrid Mapping strategy:

1.  **VLM Image Audit**: Gemini 1.5 Flash filters out blurry or poorly lit images before processing begins.
2.  **Hybrid Mapping (SfM)**: Uses original images (with background) for perfect camera triangulation, ensuring 100% stable poses.
3.  **Surgical Point-Cloud Masking**: Automatically deletes background points using AI segmentation masks before training starts.
4.  **Gaussian Splatting (30K)**: Trained on white-background datasets with 30,000 iterations for a clean, professional, floater-free 3D object.

---

## Detailed Windows Setup Guide

This engine is optimized for Windows 10/11 with NVIDIA hardware. Follow these steps carefully to ensure a successful installation.

### 1. System Requirements
- OS: Windows 10 or 11 (64-bit)
- GPU: NVIDIA RTX 30-series or 40-series (8GB+ VRAM recommended)
- RAM: 16GB minimum
- Storage: 10GB+ free space

### 2. Manual Prerequisites
- **CUDA Toolkit**: Install CUDA 11.8 or 12.1 from the NVIDIA Developer website.
- **Python 3.10**: Install from Python.org. Ensure "Add Python to PATH" is checked during installation.
- **Node.js (LTS)**: Install from nodejs.org for the orchestrator API.
- **Git**: Install Git for Windows.
- **Redis**: BullMQ requires Redis. For Windows, install [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) and run Redis inside it, or use [Memurai](https://www.memurai.com/) as a native Windows alternative.

---

## Network and IP Configuration

For the Mobile App to communicate with your Windows laptop, both devices must be on the same Wi-Fi network. You must also update the local IP address in several files.

### 1. Identify Your IP Address
Open Command Prompt on Windows and run:
```powershell
ipconfig
```
Look for "IPv4 Address" under your Wireless LAN adapter (e.g., 192.168.1.15).

### 2. Update Backend Settings
In `backend/api/.env`, update the `LOCAL_IP` variable:
```env
LOCAL_IP=192.168.x.x
```

### 3. Update AI Processor Settings
In `backend/processor/config.py`, update the fallback IP or use the `.env` file:
```python
BACKEND_URL = os.getenv("BACKEND_URL", "http://192.168.x.x:3000/api/v1")
```

### 4. Update Mobile App Settings
You must update the IP address in two repository files in the Flutter project:
- `apps/mobile_app/lib/src/features/authentication/data/auth_repository.dart`
- `apps/mobile_app/lib/src/features/reconstruction/data/project_repository.dart`

Replace `192.168.200.84` with your laptop's actual IP address.

---

## Installation Steps

### 1. Backend API Setup (Node.js)
```powershell
cd backend/api
npm install
copy .env.example .env
# Edit .env and add your MONGODB_URI and LOCAL_IP
```

### 2. AI Processor Setup (Python)
```powershell
cd backend/processor
python -m venv venv
.\venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
copy .env.example .env
# Add your Gemini API Key and Backend URL
```

### 3. Mobile App Setup (Flutter)
```powershell
cd apps/mobile_app
flutter pub get
# Ensure your IP is updated in the repository files mentioned above
flutter run
```

### 4. Execution Flow
Run these in separate terminals:
1.  **Terminal 1**: `redis-server`
2.  **Terminal 2**: `cd backend/api && npm run dev`
3.  **Terminal 3**: `cd backend/processor && .\venv\Scripts\activate && python main.py`

---

## Directory Structure

```plaintext
VokVision/
├── apps/mobile_app/        # Flutter Client (Dart)
├── backend/api/            # Node.js Orchestrator (TypeScript)
├── backend/processor/      # Python AI Engine (MASt3R, OpenSplat, VLM)
├── pipeline/               # Core AI System Modules
└── storage/                # Local data storage (Ignored by Git)
```

## Important Note on Checkpoints

The MASt3R model checkpoint (`MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth`) is required.
- It will automatically download on the first run.

---

**Pro Tip**: For best results, use 20-40 images with 360-degree coverage and consistent lighting.
