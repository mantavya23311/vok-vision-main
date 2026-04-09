"""
VokVision Local Pipeline Bypass
================================
Run this from the ROOT of your cloned vok-vision-main repo:

    cd vok-vision-main
    python run_local.py --images path/to/your/images

What this does:
  1. Copies your images into  storage/uploads/<project_id>/
  2. Builds the exact job payload that the Node.js API / BullMQ
     would normally send to the Python worker
  3. Calls backend/processor/main.py directly, bypassing Redis,
     BullMQ, Flutter, and all cloud services
  4. Output .splat lands in  storage/output/<project_id>/

Usage examples:
    python run_local.py                          # uses default test images in storage/uploads/test_project_001/
    python run_local.py --images ./my_photos/    # copy from a folder
    python run_local.py --project my_obj_scan    # custom project name
    python run_local.py --skip-vlm               # skip Gemini VLM audit (no API key needed)
"""

import argparse
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

# ── Resolve repo root (this script lives at repo root) ───────────────────────
REPO_ROOT = Path(__file__).parent.resolve()
PROCESSOR_DIR = REPO_ROOT / "backend" / "processor"
PIPELINE_DIR  = REPO_ROOT / "pipeline"
STORAGE_DIR   = REPO_ROOT / "storage"

# ── Supported image extensions ────────────────────────────────────────────────
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def make_project_id(name: str) -> str:
    """Produce a stable project ID from a name, or a random one."""
    if name:
        return name.replace(" ", "_").lower()
    return "proj_" + str(uuid.uuid4())[:8]


def copy_images(src: Path, dest: Path) -> list:
    """Copy images from src folder into dest, return list of dest paths."""
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    files = sorted([f for f in src.iterdir() if f.suffix.lower() in IMAGE_EXTS])
    if not files:
        print(f"[ERROR] No images found in {src}")
        sys.exit(1)
    for i, f in enumerate(files, 1):
        dst = dest / f"{i:03d}_{f.name}"
        shutil.copy2(f, dst)
        copied.append(str(dst))
        print(f"  [+] {f.name} → {dst.name}")
    return copied


def build_job_payload(project_id: str, image_paths: list, skip_vlm: bool, iterations: int) -> dict:
    """
    Mimics the exact BullMQ job payload the Node.js API enqueues.
    Shape inferred from the deployment doc and setup_m1.sh entry point.
    """
    return {
        "projectId":   project_id,
        "imagePaths":  image_paths,
        "outputDir":   str(STORAGE_DIR / "output" / project_id),
        "skipVlm":     skip_vlm,        # bypass Gemini audit when no API key
        "iterations":  iterations,           # OpenSplat Gaussian splatting iterations
        "localRun":    True,            # tells main.py to skip Redis result callback
    }


def check_venv():
    """Warn if not inside the processor venv."""
    venv_python = PROCESSOR_DIR / "venv" / "bin" / "python"
    if not venv_python.exists():
        print("\n[WARN] Processor venv not found at backend/processor/venv/")
        print("       Run setup first:")
        print("         cd backend/processor")
        print("         python3.10 -m venv venv")
        print("         venv/bin/pip install -r requirements.txt")
        print()
    current = Path(sys.executable)
    if "venv" not in str(current):
        print(f"[WARN] You are running with: {current}")
        print(f"       Recommended: {venv_python}")
        print(f"       Activate with: source backend/processor/venv/bin/activate")
        print()


def patch_sys_path():
    """Add processor and pipeline dirs to sys.path so imports resolve."""
    for p in [str(PROCESSOR_DIR), str(PIPELINE_DIR), str(REPO_ROOT)]:
        if p not in sys.path:
            sys.path.insert(0, p)


def run(args):
    project_id = make_project_id(args.project)
    upload_dir  = STORAGE_DIR / "uploads"  / project_id
    output_dir  = STORAGE_DIR / "outputs"   / project_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Gather images ──────────────────────────────────────────────────────
    if args.images:
        src = Path(args.images).resolve()
        if not src.exists():
            print(f"[ERROR] Image path does not exist: {src}")
            sys.exit(1)
        if src.is_file() and src.suffix.lower() in IMAGE_EXTS:
            # single file — put it in a temp folder
            tmp = STORAGE_DIR / "uploads" / (project_id + "_tmp")
            tmp.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp / src.name)
            src = tmp
        print(f"\n[1/4] Copying images from {src} → {upload_dir}")
        image_paths = copy_images(src, upload_dir)
    else:
        # default: look for images already in storage/uploads/<project_id>/
        if upload_dir.exists():
            image_paths = sorted([
                str(f) for f in upload_dir.iterdir()
                if f.suffix.lower() in IMAGE_EXTS
            ])
            if image_paths:
                print(f"\n[1/4] Using existing images in {upload_dir} ({len(image_paths)} files)")
            else:
                print(f"[ERROR] No images in {upload_dir}. Use --images to specify a source.")
                sys.exit(1)
        else:
            print(f"[ERROR] No --images provided and {upload_dir} doesn't exist.")
            print(f"        Usage: python run_local.py --images /path/to/photos/")
            sys.exit(1)

    print(f"         Total: {len(image_paths)} images")

    # ── 2. Build job payload ──────────────────────────────────────────────────
    job = build_job_payload(project_id, image_paths, args.skip_vlm, args.iterations)
    job_file = STORAGE_DIR / "uploads" / project_id / "_job.json"
    with open(job_file, "w") as f:
        json.dump(job, f, indent=2)
    print(f"\n[2/4] Job payload written → {job_file}")
    print(f"       Project ID : {project_id}")
    print(f"       Images     : {len(image_paths)}")
    print(f"       Iterations : {job['iterations']}")
    print(f"       Skip VLM   : {job['skipVlm']}")
    print(f"       Output dir : {job['outputDir']}")

    # ── 3. Inject into main.py ────────────────────────────────────────────────
    check_venv()
    patch_sys_path()

    main_py = PROCESSOR_DIR / "main.py"
    if not main_py.exists():
        print(f"\n[ERROR] {main_py} not found.")
        print("        Make sure you are running this from the repo root:")
        print("          cd vok-vision-main && python run_local.py")
        sys.exit(1)

    print(f"\n[3/4] Invoking {main_py} with local job payload...")
    print("─" * 60)

    # Set env vars that main.py reads instead of from Redis/BullMQ
    os.environ["VOK_LOCAL_RUN"]      = "1"
    os.environ["VOK_PROJECT_ID"]     = project_id
    os.environ["VOK_IMAGE_PATHS"]    = json.dumps(image_paths)
    os.environ["VOK_OUTPUT_DIR"]     = str(output_dir)
    os.environ["VOK_SKIP_VLM"]       = "1" if args.skip_vlm else "0"
    os.environ["VOK_ITERATIONS"]     = str(args.iterations)
    os.environ["VOK_JOB_FILE"]       = str(job_file)     # fallback: main.py can read JSON

    # Also write a legacy-style .env patch for processors that use python-dotenv
    env_override = PROCESSOR_DIR / ".env.local"
    with open(env_override, "w") as f:
        for k, v in os.environ.items():
            if k.startswith("VOK_"):
                f.write(f"{k}={v}\n")

    # Run main.py in-process (shares our patched sys.path and env)
    import importlib.util
    spec = importlib.util.spec_from_file_location("processor_main", main_py)
    mod  = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        if hasattr(mod, "run_pipeline"):
            print("DEBUG: Calling run_pipeline...")
            mod.run_pipeline(project_id)
        else:
            print("[ERROR] run_pipeline() not found in main.py")
            sys.exit(1)
        
    except SystemExit as e:
        # main.py may call sys.exit(0) on clean finish — that's fine
        if e.code not in (0, None):
            print(f"\n[ERROR] main.py exited with code {e.code}")
            sys.exit(e.code)

    # ── 4. Report output ──────────────────────────────────────────────────────
    print("─" * 60)
    print(f"\n[4/4] Pipeline finished. Checking output...")
    outputs = list(output_dir.iterdir()) if output_dir.exists() else []
    if outputs:
        print(f"\n Output files in {output_dir}:")
        for f in sorted(outputs):
            size = f.stat().st_size
            print(f"   {f.name}  ({size/1024:.1f} KB)")
        splat_files = [f for f in outputs if f.suffix in (".splat", ".ply", ".glb")]
        if splat_files:
            print(f"\n [SUCCESS] 3D output: {splat_files[0]}")
        else:
            print("\n [NOTE] No .splat yet — pipeline may still be running or failed mid-way.")
            print("        Check logs above for errors.")
    else:
        print(f"\n [NOTE] Output directory is empty: {output_dir}")
        print("        The pipeline may have failed before writing output.")
        print("        Check the logs above carefully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="VokVision local pipeline bypass — run reconstruction without Redis/Flutter/cloud"
    )
    parser.add_argument(
        "--images", "-i",
        help="Path to folder of input images (or single image). "
             "If omitted, uses images already in storage/uploads/<project>/",
        default=None
    )
    parser.add_argument(
        "--project", "-p",
        help="Project name / ID (default: auto-generated)",
        default="test_project_001"
    )
    parser.add_argument(
        "--skip-vlm",
        action="store_true",
        help="Skip the Gemini VLM image audit step (no API key required)"
    )
    parser.add_argument(
        "--iterations", "-n",
        type=int,
        default=30000,
        help="OpenSplat Gaussian splatting iterations (default: 30000, use 3000 for quick test)"
    )
    args = parser.parse_args()
    run(args)
