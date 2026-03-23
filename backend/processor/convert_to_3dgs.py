import os
import argparse
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as R

def convert_mast3r_to_colmap(scene_path, image_dir, output_dir):
    """
    Converts a MASt3R .glb scene into COLMAP sparse format (cameras.txt, images.txt, points3D.txt).
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading MASt3R scene from {scene_path}...")
    scene = trimesh.load(scene_path)
    
    image_files = sorted([f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    # 1. Extract Point Cloud
    points = []
    colors = []
    for geom in scene.geometry.values():
        if hasattr(geom, "vertices"):
            points.append(np.asarray(geom.vertices))
            if hasattr(geom.visual, "vertex_colors"):
                colors.append(np.asarray(geom.visual.vertex_colors)[:, :3])
            else:
                colors.append(np.ones((len(geom.vertices), 3)) * 255)
    
    if not points:
        raise ValueError("No vertices found in scene.")
        
    points = np.concatenate(points)
    colors = np.concatenate(colors)
    
    # Optional: Downsample if too heavy
    sample_size = 200000
    if len(points) > sample_size:
        idx = np.random.choice(len(points), sample_size, replace=False)
        points = points[idx]
        colors = colors[idx]

    # 2. Extract Camera Poses
    cameras_matrices = []
    for node in scene.graph.nodes:
        transform, geometry = scene.graph[node]
        if transform is not None and isinstance(transform, np.ndarray) and transform.shape == (4,4):
            cameras_matrices.append(transform)
            
    print(f"Extracted {len(points)} points and {len(cameras_matrices)} camera poses.")

    # 3. Write cameras.txt (Dummy Pinhole)
    # Note: In a production VLM setup, the VLM can provide better intrinsic hints.
    width, height = 1024, 768
    fx = fy = 800 # Approximate
    cx, cy = width / 2, height / 2
    
    with open(os.path.join(output_dir, "cameras.txt"), "w") as f:
        f.write(f"1 PINHOLE {width} {height} {fx} {fy} {cx} {cy}\n")

    # 4. Write images.txt
    with open(os.path.join(output_dir, "images.txt"), "w") as f:
        for i, img_name in enumerate(image_files):
            if i < len(cameras_matrices):
                T = cameras_matrices[i]
                Rm = T[:3, :3]
                t = T[:3, 3]
            else:
                # Fallback to identity if we have more images than poses
                Rm = np.eye(3)
                t = np.zeros(3)
                
            q = R.from_matrix(Rm).as_quat()
            # COLMAP expects qw, qx, qy, qz
            qw, qx, qy, qz = q[3], q[0], q[1], q[2]
            
            f.write(f"{i+1} {qw} {qx} {qy} {qz} {t[0]} {t[1]} {t[2]} 1 {img_name}\n\n")

    # 5. Write points3D.txt
    with open(os.path.join(output_dir, "points3D.txt"), "w") as f:
        for i, p in enumerate(points):
            r, g, b = colors[i]
            # ID X Y Z R G B ERROR(1.0)
            f.write(f"{i+1} {p[0]} {p[1]} {p[2]} {int(r)} {int(g)} {int(b)} 1.0\n")

    print(f"COLMAP dataset successfully generated in: {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to input .glb scene")
    parser.add_argument("--images", required=True, help="Path to original images directory")
    parser.add_argument("--output", required=True, help="Path to output COLMAP directory")
    args = parser.parse_args()
    
    convert_mast3r_to_colmap(args.input, args.images, args.output)
