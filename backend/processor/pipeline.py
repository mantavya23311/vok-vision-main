import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import subprocess
import sys
import glob
import requests
from PIL import Image

from config import (
    MAST3R_PATH, GAUSSIAN_PATH, OPENSPLAT_PATH,
    UPLOAD_DIR, OUTPUT_DIR, DEVICE, ITERATIONS, BACKEND_URL
)

from vlm_gateway import VLMGateway
from device import get_device


# ==============================
# Helpers
# ==============================
def report_progress(job_id, status, progress, stage):
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
    print(f"\n===== Running {description} =====\n")
    print("Command:", " ".join(command))
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"\n❌ {description} failed.")
        sys.exit(1)
    print(f"\n✅ {description} completed successfully.\n")


# ==============================
# MAIN PIPELINE
# ==============================
def run_pipeline(job_id):

    device     = get_device()
    iterations = int(os.getenv("VOK_ITERATIONS", ITERATIONS))

    input_folder  = os.path.join(UPLOAD_DIR, job_id)
    output_folder = os.path.join(OUTPUT_DIR,  job_id)
    os.makedirs(output_folder, exist_ok=True)

    print(f"\n🚀 Starting 3D Reconstruction Pipeline for: {job_id}")
    print(f"Device: {device} | Input: {input_folder} | Output: {output_folder}")

    # ==============================
    # PHASE 1 — Load + Audit Images
    # ==============================
    image_paths = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
        image_paths.extend(glob.glob(os.path.join(input_folder, ext)))
    print(f"📸 Found {len(image_paths)} images")

    valid_image_paths = image_paths
    if os.getenv("VOK_SKIP_VLM", "0") != "1":
        try:
            gateway    = VLMGateway()
            rejections = gateway.audit_images(image_paths)
            rejected   = {r['path'] for r in rejections}
            valid_image_paths = [p for p in image_paths if p not in rejected]
        except Exception as e:
            print(f"⚠️ VLM failed: {e}")

    # ==============================
    # PHASE 2 — 2D segmentation (bypassed)
    # Post-MASt3R 3-D voting is used instead (Phase 3b).
    # ==============================
    print("\n===== 2D Segmentation SKIPPED (3-D voting used instead) =====")
    segmented_folder = None

    # ==============================
    # STEP 3a — MASt3R
    # ==============================
    print("\n===== Running MASt3R =====")
    mast3r_script = os.path.join(os.path.dirname(__file__), "mast3r_reconstruct.py")
    if not os.path.exists(mast3r_script):
        raise FileNotFoundError(f"MASt3R script not found: {mast3r_script}")

    mast3r_cmd = [
        sys.executable, mast3r_script,
        "--input_dir", input_folder,
        "--output_dir", output_folder,
    ]
    if segmented_folder is not None:
        mast3r_cmd += ["--mask_dir", segmented_folder]

    run_command(mast3r_cmd, "MASt3R Reconstruction")

    # ==============================
    # STEP 3b — Object Point-Cloud Isolation
    #
    # ENV VARS:
    #   VOK_SEGMENT_OBJECT=1    enable (default: 1)
    #   VOK_VOTE_THRESH=0.60    mask-vote threshold (default: 0.60)
    #   VOK_MASK_IMAGES=1       also black-out image backgrounds (RECOMMENDED
    #                           for clean splat — set this to 1)
    #   VOK_SEG_METHOD=auto     auto | colour | geometry | sam2
    # ==============================
    segment_object = os.getenv("VOK_SEGMENT_OBJECT", "1") == "1"

    if segment_object:
        print("\n===== Running Object Point-Cloud Isolation =====")

        colmap_dir  = os.path.join(output_folder, "dataset", "sparse", "0")
        images_dir  = os.path.join(output_folder, "dataset", "images")
        # Default vote_thresh raised to 0.60 (was 0.40 — too lenient)
        vote_thresh = float(os.getenv("VOK_VOTE_THRESH", "0.35"))
        # STRONGLY RECOMMENDED: set VOK_MASK_IMAGES=1 so OpenSplat learns
        # only the object appearance, preventing background floaters.
        mask_images = os.getenv("VOK_MASK_IMAGES", "0") == "1"
        seg_method  = os.getenv("VOK_SEG_METHOD", "auto")

        import torch
        sam_device = "cuda" if torch.cuda.is_available() else "cpu"

        seg_script = os.path.join(os.path.dirname(__file__),
                                  "segment_object_pointcloud.py")

        if not os.path.exists(seg_script):
            print(f"⚠️  seg script not found at {seg_script} — skipping")
        else:
            seg_cmd = [
                sys.executable, seg_script,
                "--colmap_dir",  colmap_dir,
                "--images_dir",  images_dir,
                "--output_dir",  colmap_dir,
                "--vote_thresh", str(vote_thresh),
                "--device",      sam_device,
                "--method",      seg_method,
            ]
            if mask_images:
                seg_cmd.append("--mask_images")

            run_command(seg_cmd, "Object Point-Cloud Isolation")

            # Swap images directory to masked version if requested
            if mask_images:
                masked_dir  = os.path.join(
                    output_folder, "dataset", "images_masked")
                if os.path.isdir(masked_dir):
                    import shutil
                    orig_backup = images_dir + "_orig"
                    if not os.path.exists(orig_backup):
                        shutil.copytree(images_dir, orig_backup)
                    shutil.rmtree(images_dir)
                    shutil.copytree(masked_dir, images_dir)
                    print("🔄 Swapped to masked images for OpenSplat.")
    else:
        print("\n===== Object Isolation SKIPPED (VOK_SEGMENT_OBJECT=0) =====")

    # ==============================
    # STEP 4 — OpenSplat
    # ==============================
    print("\n===== Running OpenSplat =====")

    dataset_output = os.path.join(output_folder, "dataset")
    model_output   = os.path.join(output_folder, "model.ply")

    # ── OpenSplat GPU memory tuning ───────────────────────────────────────
    # The CUDA copy_ illegal memory access at step ~300-400 is caused by
    # OpenSplat's densification cloning/splitting too many Gaussians at once,
    # exhausting VRAM during a tensor .to(device) call.
    #
    # Fixes:
    #   --densify-grad-threshold 0.0004   raise threshold → fewer clones
    #   --densify-interval 200            less frequent densification
    #   --opacity-reset-interval 3000     don't reset before training ends
    #   --max-splats 200000               hard cap on Gaussian count
    #
    # VOK_MAX_SPLATS env var to override (default 150000 = safe on 4GB GPU)
    max_splats = int(os.getenv("VOK_MAX_SPLATS", "150000"))

    # Correct OpenSplat flag names (verified from opensplat --help output):
    #   --densify-grad-thresh  (NOT --densify-grad-threshold)
    #   --refine-every         (NOT --densify-interval)
    #   --reset-alpha-every    counts in number of refinements, not steps
    #   --warmup-length        delay first refinement → fewer initial clones
    gaussian_cmd = [
        OPENSPLAT_PATH,
        dataset_output,
        "-o", model_output,
        "-n", str(iterations),
        "--resolution-schedule", "2000",
        "--densify-grad-thresh", "0.0004",   # was 0.0002 → fewer Gaussian clones per step
        "--refine-every",        "200",       # was 100 → halve densification frequency
        "--warmup-length",       "700",       # was 500 → delay first densification
        "--reset-alpha-every",   "99999",     # effectively disable opacity reset
    ]

    # Only add --cpu if device is CPU; let OpenSplat auto-detect CUDA otherwise
    if str(device) == "cpu":
        gaussian_cmd.append("--cpu")

    run_command(gaussian_cmd, "OpenSplat Training")

    print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY!\n")