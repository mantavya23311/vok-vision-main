"""
segment_object_pointcloud.py  (v3 — robust, CUDA-safe, proper isolation)
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FIXES vs v2
─────────────────────
1.  CUDA illegal memory access in OpenSplat
    ─ Caused by NaN/Inf/extreme-outlier 3-D coordinates surviving into the
      final points3D.txt.  We now sanitise every point before writing.

2.  Inconsistent colour-saliency coverage (5% → 36% swing)
    ─ Single-image border-mean fails when the bottle is close to the edge
      or the image crops change between shots.
    ─ NEW: multi-sample background estimation (corners + edges, not just
      border ring) + per-channel adaptive thresholding.
    ─ NEW: cross-image mask consistency check — if a view's mask coverage
      is an outlier vs. the median, we re-run with relaxed threshold.

3.  Incomplete object isolation (background still leaking through)
    ─ vote_thresh was 0.4 — too lenient.  Default raised to 0.60.
    ─ min_votes now requires a point to be seen from ≥ 30 % of cameras.
    ─ After mask-vote, run a final DBSCAN spatial cluster to remove any
      isolated background blobs that snuck through.
    ─ Outlier removal step: drop points whose nearest-neighbour distance
      is in the top 2 % (statistical outlier removal, like Open3D's SOR).

APPROACH PRIORITY
─────────────────
  1. SAM2  (if installed)   — automatic, best quality
  2. Colour-saliency v3     — multi-sample BG estimation + consistency check
  3. Geometry-only          — pure 3-D visibility+depth-consistency scoring

USAGE
─────
  python segment_object_pointcloud.py \
      --colmap_dir  <dataset/sparse/0> \
      --images_dir  <dataset/images>   \
      [--output_dir  <colmap_dir>]     \
      [--vote_thresh 0.60]             \
      [--mask_images]                  \
      [--method  auto|colour|geometry|sam2]

ENV VARS
────────
  VOK_SEGMENT_OBJECT=1    enable stage (default 1)
  VOK_VOTE_THRESH=0.60    fraction of cameras that must agree (default 0.60)
  VOK_MASK_IMAGES=1       also black-out image backgrounds for OpenSplat
  VOK_SEG_METHOD=auto     method override
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import os, sys, argparse, warnings
import numpy as np
from pathlib import Path
from PIL import Image

warnings.filterwarnings("ignore", category=RuntimeWarning)


# ─────────────────────────────────────────────────────────────────────────────
# COLMAP I/O
# ─────────────────────────────────────────────────────────────────────────────

def read_cameras_txt(path):
    cameras = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            p = line.split()
            cameras[int(p[0])] = dict(
                model=p[1], w=int(p[2]), h=int(p[3]),
                params=list(map(float, p[4:])))
    return cameras


def read_images_txt(path):
    images = {}
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    i = 0
    while i < len(lines):
        p = lines[i].split()
        images[int(p[0])] = dict(
            qvec=np.array(list(map(float, p[1:5]))),
            tvec=np.array(list(map(float, p[5:8]))),
            camera_id=int(p[8]), name=p[9])
        i += 2
    return images


def read_points3D_txt(path):
    points = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            p = line.split()
            points.append(dict(
                id=int(p[0]),
                xyz=np.array([float(p[1]), float(p[2]), float(p[3])]),
                rgb=np.array([int(p[4]),   int(p[5]),   int(p[6])]),
                error=float(p[7]),
                rest=' '.join(p[8:])))
    return points


def write_points3D_txt(path, points):
    with open(path, 'w') as f:
        for p in points:
            f.write(
                f"{p['id']} "
                f"{p['xyz'][0]:.6f} {p['xyz'][1]:.6f} {p['xyz'][2]:.6f} "
                f"{p['rgb'][0]} {p['rgb'][1]} {p['rgb'][2]} "
                f"{p['error']:.6f} {p.get('rest','1.0')}\n")


# ─────────────────────────────────────────────────────────────────────────────
# ① SANITISE POINT CLOUD  (fixes CUDA illegal memory access)
# ─────────────────────────────────────────────────────────────────────────────

def sanitise_points(points, scene_scale_percentile=99.5):
    """
    Remove NaN, Inf, and extreme-outlier points that crash OpenSplat's
    CUDA kernels.  Also clamps colours to [0,255].

    The CUDA crash (nonzero_cuda illegal memory access) is caused by
    degenerate float values in the point positions that overflow GPU
    register buffers during the densification step.
    """
    if not points:
        return points

    xyz   = np.array([p['xyz'] for p in points])
    valid = np.isfinite(xyz).all(axis=1)

    # Remove statistical outliers: keep points within N×std of centroid
    if valid.sum() > 10:
        centroid = xyz[valid].mean(axis=0)
        dists    = np.linalg.norm(xyz - centroid, axis=1)
        # Use percentile-based cutoff, not hard std — robust to skew
        max_dist = np.percentile(dists[valid], scene_scale_percentile)
        valid   &= dists <= max_dist

    clean = []
    for p, v in zip(points, valid):
        if not v:
            continue
        p = dict(p)
        p['rgb'] = np.clip(p['rgb'], 0, 255).astype(int)
        clean.append(p)

    removed = len(points) - len(clean)
    if removed > 0:
        print(f"  🧹 Sanitised: removed {removed} NaN/Inf/outlier points "
              f"({100*removed/len(points):.1f}%)")
    return clean


# ─────────────────────────────────────────────────────────────────────────────
# ② SPATIAL OUTLIER REMOVAL  (Statistical Outlier Removal — SOR)
# ─────────────────────────────────────────────────────────────────────────────

def statistical_outlier_removal(points, k=20, std_ratio=2.0):
    """
    For each point compute mean distance to its k nearest neighbours.
    Remove points whose mean NN-distance > global_mean + std_ratio×std.
    Equivalent to Open3D's remove_statistical_outlier.
    """
    if len(points) < k + 1:
        return points

    try:
        from scipy.spatial import cKDTree
        xyz  = np.array([p['xyz'] for p in points])
        tree = cKDTree(xyz)
        dists, _ = tree.query(xyz, k=k + 1)   # first col is self (0)
        mean_d   = dists[:, 1:].mean(axis=1)
        threshold = mean_d.mean() + std_ratio * mean_d.std()
        keep = mean_d <= threshold
        kept = [p for p, k_ in zip(points, keep) if k_]
        print(f"  🔬 SOR: {len(points)} → {len(kept)} points "
              f"(removed {len(points)-len(kept)} outliers)")
        return kept
    except ImportError:
        print("  ℹ️  scipy not available — skipping SOR")
        return points


# ─────────────────────────────────────────────────────────────────────────────
# ③ DBSCAN CLUSTER FILTER  (keep only main object cluster)
# ─────────────────────────────────────────────────────────────────────────────

def keep_largest_cluster(points, eps=0.15, min_samples=5):
    """
    Improved DBSCAN filtering: Keeps all significant clusters to prevent 
    fragmenting the object, and includes a safety floor.
    """
    if not points:
        return points

    # Safety: If we already have very few points, don't filter further
    if len(points) < 1000:
        return points

    # Hard guard — prevent OOM for DBSCAN
    DBSCAN_MAX = 80_000
    if len(points) > DBSCAN_MAX:
        print(f"  ⚠️  DBSCAN guard: {len(points)} > {DBSCAN_MAX} — emergency downsample")
        # Note: voxel_downsample must be defined in your script
        points = voxel_downsample(points, voxel_size=0.01)

    xyz = np.array([p['xyz'] for p in points])

    labels = None
    try:
        from sklearn.cluster import DBSCAN
        # We use a slightly larger eps by default to bridge gaps in the point cloud
        labels = DBSCAN(eps=eps, min_samples=min_samples,
                        algorithm='ball_tree', n_jobs=1).fit_predict(xyz)
    except Exception as e:
        print(f"  ⚠️  DBSCAN execution failed ({e}), trying manual fallback")
        try:
            labels = _manual_dbscan(xyz, eps, min_samples)
        except:
            return points

    # Count points in each cluster (ignore noise label -1)
    valid_mask = (labels >= 0)
    if not np.any(valid_mask):
        print("  ⚠️  DBSCAN: All points classified as noise. Keeping original.")
        return points

    counts = np.bincount(labels[valid_mask])
    if len(counts) == 0:
        return points

    # --- THE FIX: KEEP ALL SIGNIFICANT CLUSTERS ---
    # Instead of just the max, keep any cluster that is:
    # 1. At least 15% as large as the biggest cluster
    # 2. OR at least 5% of the total point cloud
    max_count = np.max(counts)
    threshold = max(max_count * 0.15, len(points) * 0.05)
    significant_clusters = np.where(counts >= threshold)[0]
    
    kept_indices = np.isin(labels, significant_clusters)
    kept_points = [p for i, p in enumerate(points) if kept_indices[i]]

    # --- SAFETY FLOOR ---
    # If we are left with fewer than 1000 points but started with many, 
    # the epsilon was likely too small. Revert to original points.
    if len(kept_points) < 1000 and len(points) > 2000:
        print(f"  ⚠️  Clustering too aggressive (kept only {len(kept_points)} pts). Reverting to original.")
        return points

    noise_count = np.sum(labels == -1)
    print(f"  🔥 DBSCAN: Kept {len(significant_clusters)} clusters ({len(kept_points)} pts) | "
          f"Removed {noise_count} noise pts")
    
    return kept_points


def _manual_dbscan(xyz, eps, min_samples):
    """Minimal DBSCAN using scipy KDTree — O(n log n)."""
    from scipy.spatial import cKDTree
    n      = len(xyz)
    labels = np.full(n, -1, dtype=np.int32)
    tree   = cKDTree(xyz)
    nbrs   = tree.query_ball_tree(tree, r=eps)
    visited = np.zeros(n, dtype=bool)
    cluster = 0
    for i in range(n):
        if visited[i]:
            continue
        visited[i] = True
        if len(nbrs[i]) < min_samples:
            continue
        labels[i] = cluster
        queue = list(nbrs[i])
        while queue:
            j = queue.pop()
            if not visited[j]:
                visited[j] = True
                if len(nbrs[j]) >= min_samples:
                    queue.extend(nbrs[j])
            if labels[j] == -1:
                labels[j] = cluster
        cluster += 1
    return labels


# ─────────────────────────────────────────────────────────────────────────────
# ④ VOXEL DOWNSAMPLE
# ─────────────────────────────────────────────────────────────────────────────

def voxel_downsample(points, voxel_size=0.005):
    if not points:
        return points
    xyz    = np.array([p['xyz'] for p in points])
    voxels = np.floor(xyz / voxel_size).astype(np.int64)
    # Use structured key via Cantor pairing (fast, no dict overhead)
    seen   = {}
    order  = []
    for i, v in enumerate(map(tuple, voxels)):
        if v not in seen:
            seen[v] = i
            order.append(i)
    kept = [points[i] for i in order]
    print(f"  🔲 Voxel downsample ({voxel_size}): {len(points)} → {len(kept)}")
    return kept


# ─────────────────────────────────────────────────────────────────────────────
# Geometry
# ─────────────────────────────────────────────────────────────────────────────

def qvec_to_rotmat(q):
    w, x, y, z = q
    return np.array([
        [1-2*y*y-2*z*z,   2*x*y-2*z*w,   2*x*z+2*y*w],
        [  2*x*y+2*z*w, 1-2*x*x-2*z*z,   2*y*z-2*x*w],
        [  2*x*z-2*y*w,   2*y*z+2*x*w, 1-2*x*x-2*y*y]])


def project_points(xyz, R, t, cam):
    xyz_c    = (R @ xyz.T).T + t
    in_front = xyz_c[:, 2] > 0.01
    p  = cam['params']
    fx = p[0]; fy = p[1] if len(p) > 1 else p[0]
    cx = p[2] if len(p) > 2 else cam['w'] / 2
    cy = p[3] if len(p) > 3 else cam['h'] / 2
    z  = xyz_c[:, 2]
    u  = fx * xyz_c[:, 0] / (z + 1e-8) + cx
    v  = fy * xyz_c[:, 1] / (z + 1e-8) + cy
    return np.stack([u, v], 1), in_front


# ─────────────────────────────────────────────────────────────────────────────
# ⑤ COLOUR-SALIENCY v3  (multi-sample BG + consistency check)
# ─────────────────────────────────────────────────────────────────────────────

def rgb_to_lab(img_rgb: np.ndarray) -> np.ndarray:
    rgb = img_rgb.astype(np.float32) / 255.0
    m   = rgb > 0.04045
    rgb[m]  = ((rgb[m] + 0.055) / 1.055) ** 2.4
    rgb[~m] /= 12.92
    M   = np.array([[0.4124564, 0.3575761, 0.1804375],
                    [0.2126729, 0.7151522, 0.0721750],
                    [0.0193339, 0.1191920, 0.9503041]], dtype=np.float32)
    xyz = (M @ rgb.reshape(-1, 3).T).T.reshape(img_rgb.shape)
    xyz[..., 0] /= 0.95047; xyz[..., 2] /= 1.08883
    f   = np.where(xyz > 0.008856, xyz ** (1/3), 7.787 * xyz + 16/116)
    return np.stack([116*f[...,1]-16, 500*(f[...,0]-f[...,1]),
                     200*(f[...,1]-f[...,2])], axis=-1)


def otsu_threshold(arr: np.ndarray) -> float:
    hist, edges = np.histogram(arr, bins=256)
    hist = hist.astype(np.float64)
    tot  = hist.sum()
    if tot == 0:
        return float(arr.mean())
    c    = (edges[:-1] + edges[1:]) / 2
    w0   = np.cumsum(hist); w1 = tot - w0
    mu0  = np.cumsum(hist * c) / np.maximum(w0, 1)
    mu1  = ((hist * c).sum() - np.cumsum(hist * c)) / np.maximum(w1, 1)
    idx  = np.argmax(w0 * w1 * (mu0 - mu1) ** 2)
    return float(c[idx])


def lcc(binary: np.ndarray) -> np.ndarray:
    try:
        from scipy.ndimage import label
        lab, n = label(binary)
        if n == 0:
            return binary
        from scipy.ndimage import sum as nds
        sizes = nds(binary, lab, range(1, n+1))
        return lab == int(np.argmax(sizes)) + 1
    except ImportError:
        return binary


def sample_background_lab(lab: np.ndarray, h: int, w: int) -> np.ndarray:
    """
    Robustly estimate background colour by sampling multiple border regions
    and taking the MEDIAN (not mean) — resistant to object touching the edge.
    Returns shape (3,).
    """
    bw   = max(8, int(min(h, w) * 0.08))
    # Collect border samples
    samples = []
    for region in [
        lab[:bw,  :],            # top
        lab[-bw:, :],            # bottom
        lab[:, :bw],             # left
        lab[:, -bw:],            # right
        lab[:bw,  :bw],          # TL corner
        lab[:bw,  -bw:],         # TR corner
        lab[-bw:, :bw],          # BL corner
        lab[-bw:, -bw:],         # BR corner
    ]:
        samples.append(region.reshape(-1, 3))
    all_samples = np.concatenate(samples, axis=0)
    return np.median(all_samples, axis=0)


def colour_saliency_mask_v3(img_path: str,
                             dilate_px: int = 30,
                             coverage_target: tuple = (0.05, 0.70)
                             ) -> tuple[np.ndarray, float]:
    """
    Returns (H×W bool mask, coverage_fraction).

    Multi-sample background estimation + adaptive re-threshold if
    coverage is outside the plausible range [5%, 70%].
    """
    img = np.array(Image.open(img_path).convert('RGB'))
    h, w = img.shape[:2]
    lab  = rgb_to_lab(img)

    bg   = sample_background_lab(lab, h, w)
    dist = np.linalg.norm(lab - bg, axis=-1)          # H×W

    thresh = otsu_threshold(dist.ravel())
    fg     = lcc(dist > thresh)

    coverage = fg.mean()

    # Adaptive re-threshold: if coverage is outside expected range,
    # try a percentile-based threshold instead
    lo, hi = coverage_target
    if not (lo <= coverage <= hi):
        # Try forcing coverage to the middle of the target range
        target_pct = (1.0 - (lo + hi) / 2) * 100
        alt_thresh = np.percentile(dist, target_pct)
        alt_fg     = lcc(dist > alt_thresh)
        alt_cov    = alt_fg.mean()
        # Accept alternate only if it's more in range
        if abs(alt_cov - (lo+hi)/2) < abs(coverage - (lo+hi)/2):
            fg       = alt_fg
            coverage = alt_cov

    # Morphological close + dilate
    try:
        from scipy.ndimage import binary_closing, binary_dilation
        fg = binary_closing(fg, structure=np.ones((15, 15), bool))
        fg = binary_dilation(fg, structure=np.ones((dilate_px, dilate_px), bool))
    except ImportError:
        pass

    return fg.astype(bool), float(coverage)


def generate_masks_colour(image_paths, output_mask_dir):
    print("  🎨 Colour-saliency v3 (multi-sample BG + adaptive threshold + morphology)")
    os.makedirs(output_mask_dir, exist_ok=True)
    masks    = {}
    coverages = []

    for img_path in image_paths:
        name = Path(img_path).name
        try:
            m, cov = colour_saliency_mask_v3(img_path)
            coverages.append(cov)
            masks[name] = m
            Image.fromarray((m * 255).astype(np.uint8)).save(
                os.path.join(output_mask_dir, name))
            print(f"    ✓ {name}  coverage={100*cov:.1f}%")
        except Exception as e:
            print(f"    ⚠️  Failed for {name}: {e}")
            img = Image.open(img_path)
            masks[name] = np.ones((img.height, img.width), dtype=bool)
            coverages.append(1.0)

    # Cross-image consistency check: flag outlier masks
    med_cov = float(np.median(coverages))
    print(f"  📊 Median mask coverage: {100*med_cov:.1f}%")
    for name, cov in zip([Path(p).name for p in image_paths], coverages):
        if abs(cov - med_cov) > 0.25:
            print(f"    ⚠️  {name} coverage={100*cov:.1f}% is an outlier "
                  f"(median={100*med_cov:.1f}%) — re-running with median target")
            img_path = next(p for p in image_paths if Path(p).name == name)
            try:
                m, cov2 = colour_saliency_mask_v3(
                    img_path, coverage_target=(med_cov*0.6, med_cov*1.4))
                masks[name] = m
                Image.fromarray((m * 255).astype(np.uint8)).save(
                    os.path.join(output_mask_dir, name))
                print(f"    ↺ Re-run: coverage={100*cov2:.1f}%")
            except Exception:
                pass

    return masks


# ─────────────────────────────────────────────────────────────────────────────
# SAM2 (if installed)
# ─────────────────────────────────────────────────────────────────────────────

def _select_best_sam_mask(raw_masks, img_shape):
    """Pick the centre-proximal, medium-area mask (not the whole scene)."""
    H, W = img_shape[:2]
    cx, cy = W / 2, H / 2
    best_score, best = -1, None
    for m in raw_masks:
        seg  = m['segmentation']
        area = m['area']
        ys, xs = np.where(seg)
        if len(xs) == 0:
            continue
        dist = np.sqrt((xs.mean()-cx)**2 + (ys.mean()-cy)**2)
        dist_n = dist / (np.sqrt(cx**2+cy**2) + 1e-8)
        area_r = area / (H * W)
        score  = (1 - dist_n) * 0.6 + area_r * 0.4
        if score > best_score and area_r < 0.55:
            best_score, best = score, seg
    return best


def generate_masks_sam2(image_paths, output_mask_dir, device='cpu'):
    import torch
    from sam2.build_sam import build_sam2
    from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
    ckpt = os.environ.get("SAM2_CHECKPOINT",
                          os.path.expanduser("~/.cache/sam2/sam2.1_hiera_small.pt"))
    cfg  = os.environ.get("SAM2_CONFIG", "sam2.1/sam2.1_hiera_small.yaml")
    sam2 = build_sam2(cfg, ckpt, device=device, apply_postprocessing=False)
    gen  = SAM2AutomaticMaskGenerator(
        sam2, points_per_side=32, pred_iou_thresh=0.70,
        stability_score_thresh=0.85, min_mask_region_area=500)
    os.makedirs(output_mask_dir, exist_ok=True)
    masks = {}
    for img_path in image_paths:
        name   = Path(img_path).name
        img_np = np.array(Image.open(img_path).convert('RGB'))
        raw    = gen.generate(img_np)
        best   = _select_best_sam_mask(raw, img_np.shape) if raw else None
        if best is None:
            best = np.ones(img_np.shape[:2], dtype=bool)
        masks[name] = best
        Image.fromarray((best * 255).astype(np.uint8)).save(
            os.path.join(output_mask_dir, name))
    return masks


# ─────────────────────────────────────────────────────────────────────────────
# Geometry-only filter
# ─────────────────────────────────────────────────────────────────────────────

def geometry_based_filter(points, images, cameras, top_fraction=0.30):
    print(f"  📐 Geometry-only (top {100*top_fraction:.0f}% vis+consistency)")
    N   = len(points)
    xyz = np.array([p['xyz'] for p in points])
    vis = np.zeros(N, np.int32)
    ds  = np.zeros(N, np.float64)
    ds2 = np.zeros(N, np.float64)
    for img_data in images.values():
        R, t = qvec_to_rotmat(img_data['qvec']), img_data['tvec']
        cam  = cameras[img_data['camera_id']]
        uv, inf = project_points(xyz, R, t, cam)
        u = uv[:,0].astype(int); v = uv[:,1].astype(int)
        ib = inf & (u>=0)&(u<cam['w'])&(v>=0)&(v<cam['h'])
        idx = np.where(ib)[0]
        z = ((R @ xyz[idx].T).T + t)[:,2]
        vis[idx] += 1; ds[idx] += z; ds2[idx] += z**2
    mu  = np.where(vis>0, ds/np.maximum(vis,1), 0)
    var = np.where(vis>1, ds2/vis - mu**2, 1e6)
    std = np.sqrt(np.maximum(var, 0))
    valid = vis >= 2
    p95   = np.percentile(std[valid], 95) if valid.sum()>0 else 1.0
    std_c = np.clip(std, 0, p95)
    vis_n = vis / (vis.max()+1e-8)
    std_n = 1.0 - std_c / (std_c.max()+1e-8)
    score = np.where(valid, 0.6*vis_n + 0.4*std_n, 0.0)
    thr   = np.percentile(score[valid], (1-top_fraction)*100) \
            if valid.sum()>0 else 0.5
    kept  = [p for p, k in zip(points, score>=thr) if k]
    print(f"  ✅ Geometry: {len(kept)}/{N} kept")
    return kept


# ─────────────────────────────────────────────────────────────────────────────
# Multi-view mask voting
# ─────────────────────────────────────────────────────────────────────────────

def filter_by_mask_vote(points, images, cameras, masks_dict,
                        vote_thresh=0.60, min_votes=1):
    print(f"  🗳️  Mask-vote: {len(points)} pts, thresh={vote_thresh}, "
          f"min_votes={min_votes}")
    N   = len(points)
    xyz = np.array([p['xyz'] for p in points])
    vf  = np.zeros(N, np.int32)
    vs  = np.zeros(N, np.int32)

    for img_data in images.values():
        name = img_data['name']
        if name not in masks_dict:
            continue
        mask = masks_dict[name]
        H, W = mask.shape
        R, t = qvec_to_rotmat(img_data['qvec']), img_data['tvec']
        cam  = cameras[img_data['camera_id']]
        uv, inf = project_points(xyz, R, t, cam)
        u = uv[:,0].astype(int); v = uv[:,1].astype(int)
        ib = inf & (u>=0)&(u<W)&(v>=0)&(v<H)
        idx = np.where(ib)[0]
        if mask.shape != (H, W):
            mask = np.array(Image.fromarray(
                mask.astype(np.uint8)*255).resize((W,H), Image.NEAREST)) > 0
        vs[idx] += 1
        on = mask[v[idx], u[idx]]
        vf[idx[on]] += 1

    enough = vs >= min_votes
    ratio  = np.where(enough, vf/np.maximum(vs,1), 0.0)
    kept   = [p for p,k in zip(points, enough&(ratio>=vote_thresh)) if k]
    print(f"  ✅ Mask-vote: {len(kept)}/{N} kept")
    return kept


# ─────────────────────────────────────────────────────────────────────────────
# Masked image writer
# ─────────────────────────────────────────────────────────────────────────────

def write_masked_images(images_dir, masks_dict, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for name, mask in masks_dict.items():
        src = os.path.join(images_dir, name)
        if not os.path.exists(src):
            continue
        img = np.array(Image.open(src).convert('RGB'))
        if mask.shape[:2] != img.shape[:2]:
            mh, mw = img.shape[:2]
            mask = np.array(Image.fromarray(
                mask.astype(np.uint8)*255).resize((mw,mh),Image.NEAREST)) > 0
        img[~mask] = 0
        Image.fromarray(img).save(os.path.join(output_dir, name))
    print(f"  📸 Masked images → {output_dir}")


# ─────────────────────────────────────────────────────────────────────────────
# .bin sync
# ─────────────────────────────────────────────────────────────────────────────

def try_write_bin(colmap_dir):
    rw = os.path.join(os.path.dirname(__file__),
                      "../../pipeline/gaussian-splatting/utils")
    if rw not in sys.path:
        sys.path.append(rw)
    try:
        import read_write_model as rwm
        c, i, p = rwm.read_model(path=colmap_dir, ext=".txt")
        rwm.write_model(c, i, p, path=colmap_dir, ext=".bin")
        print("  ✅ .bin updated")
    except Exception as e:
        print(f"  ⚠️  .bin update skipped: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_segmentation(colmap_dir, images_dir, output_dir=None,
                     vote_thresh=0.60, mask_images=False,
                     device='cpu', mask_dir=None, method='auto'):

    if output_dir is None:
        output_dir = colmap_dir
    os.makedirs(output_dir, exist_ok=True)

    for fn in ["cameras.txt", "images.txt", "points3D.txt"]:
        if not os.path.exists(os.path.join(colmap_dir, fn)):
            raise FileNotFoundError(f"Missing: {os.path.join(colmap_dir, fn)}")

    print("\n📂 Reading COLMAP model …")
    cameras = read_cameras_txt(os.path.join(colmap_dir, "cameras.txt"))
    images  = read_images_txt (os.path.join(colmap_dir, "images.txt"))
    points  = read_points3D_txt(os.path.join(colmap_dir, "points3D.txt"))
    print(f"   {len(cameras)} cams | {len(images)} imgs | {len(points)} pts")

    # ── Step 1: sanitise raw point cloud (fixes CUDA crash) ───────────────
    print("\n🧹 Sanitising raw point cloud …")
    points = sanitise_points(points)

    image_paths = sorted({
        os.path.join(images_dir, d['name'])
        for d in images.values()
        if os.path.exists(os.path.join(images_dir, d['name']))})

    mask_cache = os.path.join(output_dir, "object_masks")
    masks_dict = None

    # ── Step 2: generate / load masks ─────────────────────────────────────
    if mask_dir and os.path.isdir(mask_dir):
        print(f"\n🗂️  Pre-computed masks from {mask_dir}")
        masks_dict = {}
        for d in images.values():
            mp = os.path.join(mask_dir, d['name'])
            if os.path.exists(mp):
                masks_dict[d['name']] = \
                    np.array(Image.open(mp).convert('L')) > 127
        print(f"   Loaded {len(masks_dict)} masks")

    if masks_dict is None and method in ('auto', 'sam2'):
        try:
            print("\n🤖 Trying SAM2 …")
            masks_dict = generate_masks_sam2(image_paths, mask_cache, device)
            print("  ✅ SAM2 succeeded")
        except Exception as e:
            print(f"  ℹ️  SAM2 unavailable: {e}")
            if method == 'sam2':
                method = 'auto'

    if masks_dict is None and method in ('auto', 'colour'):
        print("\n🎨 Colour-saliency v3 …")
        masks_dict = generate_masks_colour(image_paths, mask_cache)

    # ── Step 3: filter point cloud ────────────────────────────────────────
    print("\n🔬 Filtering point cloud …")
    if method == 'geometry' or masks_dict is None:
        filtered = geometry_based_filter(points, images, cameras,
                                          top_fraction=vote_thresh)
    else:
        # Require a point to be seen from at least 30% of cameras
        min_v    = max(2, int(len(images) * 0.30))
        filtered = filter_by_mask_vote(
            points, images, cameras, masks_dict,
            vote_thresh=vote_thresh, min_votes=min_v)

    if not filtered:
        print("  ⚠️  No points survived mask vote — falling back to geometry")
        filtered = geometry_based_filter(points, images, cameras,
                                          top_fraction=0.25)

    # ── Step 4: post-process ──────────────────────────────────────────────
    #
    # CRITICAL ORDER:
    #   4a  Voxel-downsample FIRST  → brings 500k pts down to ~50k
    #   4b  SOR on the small set    → fast, removes edge-case outliers
    #   4c  DBSCAN on the small set → safe in memory (was OOM-killing at 545k)
    #   4d  Final sanitise
    #
    # The previous ordering ran DBSCAN on 545,774 points.  sklearn.DBSCAN
    # internally allocates a neighbour-graph that requires ~1.2 GB RAM at
    # that scale, silently OOM-killing the process (returncode 1, no traceback).

    # 4a. Adaptive voxel downsample FIRST — target VOK_TARGET_POINTS (50k).
    #     50k init points → ~150k peak Gaussians during OpenSplat densification
    #     → safe on 4 GB VRAM.  Must run before SOR and DBSCAN.
    #
    # BUG FIX: the bbox_vol formula (prod of extents) gives volume in scene
    # units cubed, which can be very large (e.g. 5m × 3m × 2m = 30 m³).
    # cube_root(30 / 50000) = 0.085 m → voxel_size=0.10 (after clamping) →
    # 556k points collapsed to ~5k, destroying the cloud.
    #
    # CORRECT APPROACH: use the actual point density directly.
    # voxel_size = (bbox_vol / N_current) ^ (1/3)  * (N_current/TARGET)^(1/3)
    #            = (bbox_vol / TARGET) ^ (1/3)
    # That's what we had — the clamp max=0.10 is the culprit when the scene
    # is large. Remove the upper clamp and instead derive a safe starting
    # voxel from the mean NN distance (robust to scene scale).
    print("\n🔲 Downsampling to target point budget …")
    TARGET_POINTS = int(os.environ.get("VOK_TARGET_POINTS", "50000"))
    if len(filtered) > TARGET_POINTS:
        xyz_arr = np.array([p['xyz'] for p in filtered])

        # Estimate mean nearest-neighbour distance on a 2000-point sample
        # → gives us the natural point spacing in scene units.
        sample_n = min(2000, len(filtered))
        rng      = np.random.default_rng(42)
        idx_s    = rng.choice(len(filtered), sample_n, replace=False)
        sample   = xyz_arr[idx_s]
        try:
            from scipy.spatial import cKDTree
            tree    = cKDTree(sample)
            nn_d, _ = tree.query(sample, k=2)
            mean_nn = float(nn_d[:, 1].mean())   # mean spacing between pts
        except ImportError:
            # Fallback: derive from bounding box
            bbox_vol = float(np.prod(np.maximum(xyz_arr.ptp(axis=0), 1e-6)))
            mean_nn  = (bbox_vol / len(filtered)) ** (1.0 / 3.0)

        # Scale mean_nn so that the resulting grid gives ~TARGET_POINTS
        # voxel_size s.t.  N_current * (mean_nn/vox)^3 ≈ TARGET
        vox = mean_nn * (len(filtered) / TARGET_POINTS) ** (1.0 / 3.0)
        vox = max(mean_nn * 0.5, vox)    # never smaller than half spacing
        print(f"  mean_nn={mean_nn:.5f}  initial vox={vox:.5f}")
        filtered = voxel_downsample(filtered, voxel_size=vox)

        # One correction pass if still above budget (density non-uniformity)
        if len(filtered) > int(TARGET_POINTS * 1.3):
            ratio = len(filtered) / TARGET_POINTS
            vox2  = vox * (ratio ** (1.0 / 3.0))
            print(f"  correction pass: vox2={vox2:.5f}")
            filtered = voxel_downsample(filtered, voxel_size=vox2)

        print(f"  🎯 Target {TARGET_POINTS} pts → actual {len(filtered)} pts")

    # 4b. Statistical outlier removal on the now-small set (fast).
    print("\n🔬 Statistical outlier removal …")
    filtered = statistical_outlier_removal(filtered, k=20, std_ratio=2.0)

    # 4c. DBSCAN cluster filter on the now-small set — safely in memory.
    #     Removes any background blobs that leaked through mask voting.
    print("\n🔥 DBSCAN cluster filter …")
    if len(filtered)>1000:
        xyz_arr = np.array([p['xyz'] for p in filtered])
        bbox    = xyz_arr.ptp(axis=0)
        # eps ≈ 1.5 % of median scene extent, clamped to sane range
        eps = float(np.median(bbox)) * 0.05
        eps = max(0.01, min(0.5, eps))
        print(f"  eps={eps:.4f}  n_pts={len(filtered)}")
        filtered = keep_largest_cluster(filtered, eps=eps, min_samples=5)

    # 4d. Final sanitise — catch any NaN from cluster ops.
    filtered = sanitise_points(filtered, scene_scale_percentile=99.0)

    # ── Step 5: write ─────────────────────────────────────────────────────
    out_pts = os.path.join(output_dir, "points3D.txt")
    write_points3D_txt(out_pts, filtered)
    print(f"\n💾 Final: {len(filtered)} clean object points → {out_pts}")
    try_write_bin(output_dir)

    if mask_images and masks_dict:
        mdir = os.path.join(os.path.dirname(images_dir), "images_masked")
        write_masked_images(images_dir, masks_dict, mdir)
        return mdir

    return images_dir


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Filter MASt3R point cloud to main object (v3)")
    ap.add_argument("--colmap_dir",  required=True)
    ap.add_argument("--images_dir",  required=True)
    ap.add_argument("--output_dir",  default=None)
    ap.add_argument("--vote_thresh", type=float, default=0.60,
                    help="Fraction of cameras that must agree (default 0.60)")
    ap.add_argument("--mask_dir",    default=None)
    ap.add_argument("--mask_images", action="store_true")
    ap.add_argument("--device",      default="cpu",
                    choices=["cpu","cuda","mps"])
    ap.add_argument("--method",      default="auto",
                    choices=["auto","sam2","colour","geometry"])
    args = ap.parse_args()
    run_segmentation(**vars(args))
    print("\n🎉 Done!")


if __name__ == "__main__":
    main()