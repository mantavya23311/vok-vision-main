#import os
#import subprocess
#from config import MAST3R_PATH, GAUSSIAN_PATH
#
#def run_pipeline(job_id):
#    input_folder = f"uploads/{job_id}"
#    output_folder = f"outputs/{job_id}"
#    os.makedirs(output_folder, exist_ok=True)
#
#    # Step 1 — Run MASt3R
#    subprocess.run([
#        "python",
#        f"{MAST3R_PATH}/run_mast3r.py",
#        "--input_dir", input_folder,
#        "--output_dir", f"{output_folder}/mast3r",
#        "--mode", "sfm"
#    ])
#
#    # Step 2 — Convert output to 3DGS format
#    subprocess.run([
#        "python",
#        "convert_to_3dgs.py",
#        "--input", f"{output_folder}/mast3r",
#        "--output", f"{output_folder}/dataset"
#    ])
#
#    # Step 3 — Train Gaussian Splatting
#    subprocess.run([
#        "python",
#        f"{GAUSSIAN_PATH}/train.py",
#        "--model_path", f"{output_folder}/model",
#        "--iterations", "5000"
#    ])
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import subprocess
import shutil
import sys
import glob
import requests

from config import (
    MAST3R_PATH, GAUSSIAN_PATH, OPENSPLAT_PATH,
    UPLOAD_DIR, OUTPUT_DIR, DEVICE, ITERATIONS, BACKEND_URL
)
from vlm_gateway import VLMGateway
from device import get_device
from PIL import Image

def report_progress(job_id, status, progress, stage):
    """Sends a progress update to the Node.js backend."""
    try:
        url = f"{BACKEND_URL}/projects/{job_id}/progress"
        requests.post(url, json={
            "status": status,
            "progressPercentage": progress,
            "currentStage": stage
        }, timeout=5)
        print(f"📡 Progress: {stage} ({progress}%)")
    except Exception as e:
        print(f"⚠️ Failed to report progress: {e}")

def run_command(command, description):
    """
    Runs a subprocess command safely and stops if it fails.
    """
    print(f"\n===== Running {description} =====\n")
    print("Command:", " ".join(command))

    # Allow PyTorch MPS to bypass the 70% soft lock and use unlimited SSD swap on 8GB Macs
    env = os.environ.copy()
    env["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"

    result = subprocess.run(command, env=env)

    if result.returncode != 0:
        print(f"\n {description} failed.") # Changed stage_name to description for consistency
        sys.exit(1)

    print(f"\n✅ {description} completed successfully.\n") # Changed stage_name to description for consistency


def run_pipeline(job_id):
    # ==============================
    # Setup Paths & Device
    # ==============================
    device = get_device()
    
    input_folder = os.path.join(UPLOAD_DIR, job_id)
    output_folder = os.path.join(OUTPUT_DIR, job_id)

    mast3r_output = os.path.join(output_folder, "mast3r")
    dataset_output = os.path.join(output_folder, "dataset")
    model_output = os.path.join(output_folder, "model.ply")

    if not os.path.exists(input_folder):
        raise ValueError(f"Input folder does not exist: {input_folder}")

    os.makedirs(output_folder, exist_ok=True)

    print(f"\n🚀 Starting 3D Reconstruction Pipeline for: {job_id}")
    print(f"Device: {device}")
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")

    report_progress(job_id, "AUDITING", 10, "Gemini is auditing images...")
    # ==============================
    # PHASE 1 — VLM Image Audit
    # ==============================
    print("\n===== Running VLM Image Audit =====")
    valid_image_paths = []
    try:
        gateway = VLMGateway()
        image_paths = glob.glob(os.path.join(input_folder, "*.[jJ][pP][gG]")) + \
                      glob.glob(os.path.join(input_folder, "*.[pP][nN][gG]"))
        
        rejections = gateway.audit_images(image_paths)
        rejected_paths = {r['path'] for r in rejections}
        
        for p in image_paths:
            if p not in rejected_paths:
                valid_image_paths.append(p)
            else:
                print(f"🚫 Removing bad image: {os.path.basename(p)}")
                
        if len(valid_image_paths) < 10:
             print(f"⚠️ Warning: Only {len(valid_image_paths)} images passed audit. Quality may be low.")
    except Exception as e:
        print(f"⚠️ VLM Audit skipped: {e}")
        valid_image_paths = image_paths

    report_progress(job_id, "SEGMENTING", 20, "Removing background from images...")
    # ==============================
    # PHASE 2 — Segmentation (Rembg)
    # ==============================
    segmented_folder = os.path.join(output_folder, "segmented")
    try:
        from segmentation_gateway import SegmentationGateway
        seg_gateway = SegmentationGateway()
        seg_gateway.segment_images(valid_image_paths, segmented_folder)
    except Exception as e:
        print(f"⚠️ Segmentation failed, using original images: {e}")
        segmented_folder = input_folder # Fallback to original

    report_progress(job_id, "MAPPING", 35, "MASt3R is calculating camera poses...")
    # ==============================
    # STEP 1 — Run MASt3R (Mapping)
    # ==============================
    # Elite Hybrid Flow: Use original input for SfM (Background helps triangulation)
    # But pass the segmented folder as a mask to filter the point cloud
    mast3r_command = [
        sys.executable,
        "mast3r_reconstruct.py",
        "--input_dir", input_folder,
        "--output_dir", output_folder,
        "--device", str(device),
        "--image_size", "1024",
        "--iterations", "300",
        "--mask_dir", segmented_folder
    ]

    run_command(mast3r_command, "MASt3R SfM Reconstruction")

    report_progress(job_id, "TRAINING", 60, "Training Gaussian Splatting (Painting)...")
    # ==============================
    # STEP 3 — Train Gaussian Splatting
    # ==============================
    # Professional Mode: Always use --white_background for segmented objects
    if str(device) == "mps":
        # M1/M2 Mac — OpenSplat must use --cpu since Metal is not compiled
        gaussian_command = [
            OPENSPLAT_PATH,
            dataset_output,
            "-o", model_output,
            "-n", str(ITERATIONS),
            "--cpu",
            "--white_background"
        ]
        run_command(gaussian_command, "OpenSplat Training (CPU Fallback)")
    elif str(device) == "cuda":
        # NVIDIA GPU — Full power, no restrictions
        gaussian_command = [
            OPENSPLAT_PATH,
            dataset_output,
            "-o", model_output,
            "-n", str(ITERATIONS),
            "--white_background"
        ]
        run_command(gaussian_command, "OpenSplat Training (CUDA GPU)")
    else:
        # Standard 3DGS for NVIDIA/Windows
        gaussian_command = [
            sys.executable,
            os.path.join(GAUSSIAN_PATH, "train.py"),
            "-s", dataset_output,
            "--model_path", model_output,
            "--iterations", str(ITERATIONS)
        ]
        run_command(gaussian_command, "Gaussian Splatting Training (CUDA)")

    report_progress(job_id, "LIBRARIAN", 90, "Generating professional metadata (tags/title)...")
    # ==============================
    # STEP 4 — The Librarian (Auto-Meta)
    # ==============================
    metadata_str = "Untitled Project | 3D, Scan | Professional 3D reconstruction."
    try:
        # Use one of the valid images for context
        if valid_image_paths:
            sample_image = valid_image_paths[0]
            metadata_prompt = "Generate a professional title, 3 descriptive tags, and a 1-sentence summary for this 3D reconstructed object. Format: Title | Tag1, Tag2, Tag3 | Summary"
            
            with open(sample_image, 'rb') as f:
                img = Image.open(f)
                # Re-initialize gateway to ensure model access
                gateway = VLMGateway()
                response = gateway.model.generate_content([metadata_prompt, img])
                print(f"📚 Librarian Metadata: {response.text}")
                metadata_str = response.text.strip()
    except Exception as e:
        print(f"⚠️ Librarian stage failed: {e}")

    report_progress(job_id, "COMPLETED", 100, f"Finishing up! {metadata_str}")
    print("\n🎉 FULL PIPELINE COMPLETED SUCCESSFULLY!\n")
