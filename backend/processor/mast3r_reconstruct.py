import os
import sys
import torch
import numpy as np
import argparse
from pathlib import Path
from scipy.spatial.transform import Rotation as R
from pillow_heif import register_heif_opener

register_heif_opener()

# Set OpenMP fix early
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Add parent and mast3r paths (relative to backend/processor)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(BASE_DIR, "../../pipeline/mast3r")))
sys.path.append(os.path.abspath(os.path.join(BASE_DIR, "../../pipeline/mast3r/dust3r")))

from mast3r.model import AsymmetricMASt3R
from mast3r.image_pairs import make_pairs
from mast3r.cloud_opt.sparse_ga import sparse_global_alignment
from dust3r.utils.image import load_images
from dust3r.utils.device import to_numpy

def main():
    parser = argparse.ArgumentParser(description="Integrated MASt3R SfM and COLMAP Export")
    parser.add_argument("--input_dir", required=True, help="Directory containing images")
    parser.add_argument("--output_dir", required=True, help="Directory for SfM output")
    parser.add_argument("--mask_dir", default=None, help="Optional directory for segmentation masks to filter points")
    
    args = parser.parse_args()
    
    device = args.device
    if device == "mps" and not torch.backends.mps.is_available():
        device = "cpu"
        
    print(f"🚀 Initializing MASt3R SfM on {device}...")
    
    # 1. Load Images & Optional Masks
    filelist = sorted([str(p) for p in Path(args.input_dir).glob("*.[jJ][pP][gG]")])
    if not filelist:
         filelist = sorted([str(p) for p in Path(args.input_dir).glob("*.[pP][nN][gG]")])
         
    if not filelist:
        print(f" No images found in {args.input_dir}")
        sys.exit(1)
        
    print(f"📸 Found {len(filelist)} images.")
    imgs = load_images(filelist, size=args.image_size)
    
    # Pre-load masks if provided
    masks = []
    if args.mask_dir:
        from PIL import Image
        for path in filelist:
            mask_path = os.path.join(args.mask_dir, os.path.basename(path))
            if os.path.exists(mask_path):
                # Load mask, resize to match MASt3R processing size, and convert to binary
                m = Image.open(mask_path).convert('L').resize((args.image_size, args.image_size))
                # For segmented images (white background), pixels < 250 are likely the object
                masks.append(np.array(m) < 250) 
            else:
                masks.append(None)

    # 2. Load Model
    # Note: Using small model for first pass if needed, but the user expects premium results.
    model_name = "naver/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric"
    model = AsymmetricMASt3R.from_pretrained(model_name).to(device)
    
    # 3. Generate Pairs (Complete Graph for small sets, Dense Window for large sets)
    if len(imgs) <= 40:
        print(f"🤝 Generating complete image pairs (Highest Accuracy)...")
        pairs = make_pairs(imgs, scene_graph="complete", prefilter=None, symmetrize=True)
    else:
        print(f"🤝 Generating dense sliding window pairs (swin-3-noncyclic)...")
        pairs = make_pairs(imgs, scene_graph="swin-3-noncyclic", prefilter=None, symmetrize=True)
    
    # 4. Sparse Global Alignment
    cache_dir = os.path.join(args.output_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    print(f"🧩 Running Global Alignment (SfM) with {args.iterations} iterations...")
    scene = sparse_global_alignment(filelist, pairs, cache_dir, model, device=device, 
                                    niter1=args.iterations, niter2=args.iterations)
    
    # 5. Extract Results
    focals = to_numpy(scene.get_focals())
    poses = to_numpy(scene.get_im_poses()) # cam2world
    pts3d, depthmaps, confs = scene.get_dense_pts3d(clean_depth=False)
    
    # Ensure list of tensors are converted correctly
    pts3d = [to_numpy(p) for p in pts3d]
    confs = [to_numpy(c) for c in confs]
    
    # 6. Export to COLMAP Format for 3DGS
    dataset_dir = os.path.join(args.output_dir, "dataset")
    colmap_dir = os.path.join(dataset_dir, "sparse/0")
    os.makedirs(colmap_dir, exist_ok=True)
    
    # Create images symlink (Crucial: Training images are the segmented ones!)
    images_link = os.path.join(dataset_dir, "images")
    training_images = args.mask_dir if args.mask_dir else args.input_dir
    if not os.path.exists(images_link):
        try:
            os.symlink(training_images, images_link)
        except:
            import shutil
            shutil.copytree(training_images, images_link)

    print(f"💾 Exporting COLMAP format to {colmap_dir}...")
    
    # cameras.txt
    with open(os.path.join(colmap_dir, "cameras.txt"), "w") as f:
        for i, focal in enumerate(focals):
            h, w = imgs[i]['true_shape'][0]
            cx, cy = w / 2, h / 2
            f.write(f"{i+1} PINHOLE {w} {h} {focal} {focal} {cx} {cy}\n")
            
    # images.txt
    with open(os.path.join(colmap_dir, "images.txt"), "w") as f:
        for i, c2w in enumerate(poses):
            # Convert cam2world to world2cam for COLMAP
            w2c = np.linalg.inv(c2w)
            rot = w2c[:3, :3]
            t = w2c[:3, 3]
            
            q = R.from_matrix(rot).as_quat() # x, y, z, w
            qw, qx, qy, qz = q[3], q[0], q[1], q[2]
            
            img_name = Path(filelist[i]).name
            f.write(f"{i+1} {qw} {qx} {qy} {qz} {t[0]} {t[1]} {t[2]} {i+1} {img_name}\n\n")
            
    # points3D.txt (Sparsified for 3DGS init)
    with open(os.path.join(colmap_dir, "points3D.txt"), "w") as f:
        point_id = 1
        for i, (pts, conf) in enumerate(zip(pts3d, confs)):
            # Use medium-high confidence points for dense initialization
            mask_conf = conf.ravel() > 1.0
            
            # Apply optional segmentation mask to pts
            if masks[i] is not None:
                mask_seg = masks[i].ravel()
                final_mask = mask_conf & mask_seg
            else:
                final_mask = mask_conf
                
            valid_pts = pts.reshape(-1, 3)[final_mask]
            
            # Map colors from image
            img = imgs[i]['img']
            if img.ndim == 4:
                img = img.squeeze(0)
            img = img.permute(1, 2, 0).cpu().numpy() * 0.5 + 0.5
            img = (img * 255).astype(np.uint8)
            
            # Extract true colors matching the valid points
            colors = img.reshape(-1, 3)[final_mask]
            
            # Subsample for initialization (keep more for better quality)
            if len(valid_pts) > 50000:
                step = len(valid_pts) // 50000
                valid_pts = valid_pts[::step]
                colors = colors[::step]
                
            for p, c in zip(valid_pts, colors):
                f.write(f"{point_id} {p[0]} {p[1]} {p[2]} {c[0]} {c[1]} {c[2]} 1.0\n")
                point_id += 1
    # Convert .txt to .bin for OpenSplat
    print("\n🔄 Converting COLMAP .txt to .bin for OpenSplat compatibility...")
    import sys
    utils_path = os.path.join(os.path.dirname(__file__), "../../pipeline/gaussian-splatting/utils")
    if utils_path not in sys.path:
        sys.path.append(utils_path)
    try:
        import read_write_model
        cameras, images, points3D = read_write_model.read_model(path=colmap_dir, ext=".txt")
        read_write_model.write_model(cameras, images, points3D, path=colmap_dir, ext=".bin")
        print("✅ Conversion to .bin successful.")
    except Exception as e:
        print(f"⚠️ Failed to convert to .bin: {e}")

    print("\n✅ MASt3R SfM and COLMAP Export complete!")

if __name__ == "__main__":
    main()
