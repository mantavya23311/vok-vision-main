#import trimesh
#import os
#
#scene = trimesh.load("/home/mantavya23311/backend_app/reconstruction/tmp459w8g9f_scene.glb")
#
#os.makedirs("colmap_sparse/0", exist_ok=True)
#
#with open("colmap_sparse/0/cameras.txt", "w") as f:
#    f.write("# Camera list\n")
#
#with open("colmap_sparse/0/images.txt", "w") as f:
#    f.write("# Image list\n")
#
#with open("colmap_sparse/0/points3D.txt", "w") as f:
#    f.write("# Points\n")
#
#print("Scene loaded:", scene)
#import os
#import numpy as np
#import trimesh
#from scipy.spatial.transform import Rotation as R
#
#scene_path = "/home/mantavya23311/backend_app/reconstruction/tmp459w8g9f_scene.glb"
#output_dir = "/home/mantavya23311/gaussian-splatting/data/bottle/sparse/0"
#
#os.makedirs(output_dir, exist_ok=True)
#
#scene = trimesh.load(scene_path)
#
#cameras = []
#images = []
#points = []
#
#cam_id = 1
#img_id = 1
#pt_id = 1
#
#for name, geom in scene.geometry.items():
#    if not hasattr(geom, "vertices"):
#        continue
#
#    verts = np.array(geom.vertices)
#
#    for v in verts:
#        points.append((pt_id, v[0], v[1], v[2]))
#        pt_id += 1
#
## Dummy camera (MASt3R GLB does not store full COLMAP intrinsics)
#width = 512
#height = 384
#fx = fy = 500
#cx = width / 2
#cy = height / 2
#
#cameras.append((1, "PINHOLE", width, height, fx, fy, cx, cy))
#
## Fake camera poses (identity poses for all images)
#image_folder = "/home/mantavya23311/gaussian-splatting/data/bottle/images"
#image_files = sorted(os.listdir(image_folder))
#
#for img in image_files:
#    q = R.from_euler('xyz', [0,0,0]).as_quat()
#    t = np.array([0,0,0])
#
#    images.append((img_id, q[3], q[0], q[1], q[2],
#                   t[0], t[1], t[2], cam_id, img))
#
#    img_id += 1
#
## Write cameras.txt
#with open(os.path.join(output_dir, "cameras.txt"), "w") as f:
#    f.write("# Camera list\n")
#    for c in cameras:
#        f.write("{} {} {} {} {} {} {} {}\n".format(*c))
#
## Write images.txt
#with open(os.path.join(output_dir, "images.txt"), "w") as f:
#    f.write("# Image list\n")
#    for img in images:
#        f.write("{} {} {} {} {} {} {} {} {} {}\n".format(*img))
#        f.write("\n")
#
## Write points3D.txt
#with open(os.path.join(output_dir, "points3D.txt"), "w") as f:
#    f.write("# 3D points\n")
#    for p in points:
#        f.write("{} {} {} {} 255 255 255 1\n".format(*p))
#
#print("Conversion finished.")
#print("Output saved to:", output_dir)
#import os
#import numpy as np
#import trimesh
#from scipy.spatial.transform import Rotation as R
#
## ----------------------------
## PATHS
## ----------------------------
#scene_path = "/home/mantavya23311/backend_app/reconstruction/tmp459w8g9f_scene.glb"
#output_dir = "/home/mantavya23311/gaussian-splatting/data/bottle/sparse/0"
#image_folder = "/home/mantavya23311/gaussian-splatting/data/bottle/images"
#
#os.makedirs(output_dir, exist_ok=True)
#
## ----------------------------
## LOAD MAST3R SCENE
## ----------------------------
#print("Loading MASt3R scene...")
#scene = trimesh.load(scene_path)
#
#points = []
#
#for geom in scene.geometry.values():
#    if hasattr(geom, "vertices"):
#        verts = np.array(geom.vertices)
#        points.append(verts)
#
#points = np.concatenate(points)
#
#print("Original points:", len(points))
#
## ----------------------------
## DOWNSAMPLE POINT CLOUD
## ----------------------------
#sample_size = 200000
#
#if len(points) > sample_size:
#    idx = np.random.choice(len(points), sample_size, replace=False)
#    points = points[idx]
#
#print("Downsampled points:", len(points))
#
## ----------------------------
## CAMERA PARAMETERS
## ----------------------------
#width = 512
#height = 384
#fx = fy = 500
#cx = width / 2
#cy = height / 2
#
## ----------------------------
## WRITE cameras.txt
## ----------------------------
#print("Writing cameras.txt...")
#
#with open(os.path.join(output_dir, "cameras.txt"), "w") as f:
#    f.write("# Camera list\n")
#    f.write(f"1 PINHOLE {width} {height} {fx} {fy} {cx} {cy}\n")
#
## ----------------------------
## WRITE images.txt
## ----------------------------
#print("Writing images.txt...")
#
#image_files = sorted(os.listdir(image_folder))
#
#with open(os.path.join(output_dir, "images.txt"), "w") as f:
#
#    for i, img in enumerate(image_files):
#
#        q = R.from_euler('xyz', [0,0,0]).as_quat()
#        t = np.array([0,0,0])
#
#        f.write(
#            f"{i+1} {q[3]} {q[0]} {q[1]} {q[2]} "
#            f"{t[0]} {t[1]} {t[2]} 1 {img}\n\n"
#        )
#
## ----------------------------
## WRITE points3D.txt
## ----------------------------
#print("Writing points3D.txt...")
#
#with open(os.path.join(output_dir, "points3D.txt"), "w") as f:
#
#    for i, p in enumerate(points):
#        f.write(f"{i} {p[0]} {p[1]} {p[2]} 255 255 255 1\n")
#
#print("\nConversion finished.")
#print("Output saved to:", output_dir)
#import os
#import numpy as np
#import trimesh
#from pygltflib import GLTF2
#from scipy.spatial.transform import Rotation as R
#
## ----------------------------
## PATHS
## ----------------------------
#scene_path = "/home/mantavya23311/backend_app/reconstruction/tmp459w8g9f_scene.glb"
#output_dir = "/home/mantavya23311/gaussian-splatting/data/bottle/sparse/0"
#image_folder = "/home/mantavya23311/gaussian-splatting/data/bottle/images"
#
#os.makedirs(output_dir, exist_ok=True)
#
## ----------------------------
## LOAD GEOMETRY
## ----------------------------
#print("Loading MASt3R scene geometry...")
#
#scene = trimesh.load(scene_path)
#
#points = []
#
#for geom in scene.geometry.values():
#    if hasattr(geom, "vertices"):
#        verts = np.array(geom.vertices)
#        points.append(verts)
#
#points = np.concatenate(points)
#
#print("Original points:", len(points))
#
## ----------------------------
## DOWNSAMPLE
## ----------------------------
#sample_size = 200000
#
#if len(points) > sample_size:
#    idx = np.random.choice(len(points), sample_size, replace=False)
#    points = points[idx]
#
#print("Downsampled points:", len(points))
#
## ----------------------------
## LOAD CAMERA POSES FROM GLB
## ----------------------------
#print("Reading camera poses...")
#
#gltf = GLTF2().load(scene_path)
#
#cameras = []
#poses = []
#
#for node in gltf.nodes:
#
#    if node.matrix is not None:
#
#        mat = np.array(node.matrix).reshape(4,4)
#
#        R_mat = mat[:3,:3]
#        t = mat[:3,3]
#
#        q = R.from_matrix(R_mat).as_quat()
#
#        poses.append((q,t))
#
#print("Detected cameras:", len(poses))
#
## ----------------------------
## CAMERA INTRINSICS
## ----------------------------
#width = 512
#height = 384
#fx = fy = 500
#cx = width/2
#cy = height/2
#
## ----------------------------
## WRITE cameras.txt
## ----------------------------
#print("Writing cameras.txt")
#
#with open(os.path.join(output_dir,"cameras.txt"),"w") as f:
#
#    f.write("# Camera list\n")
#    f.write(f"1 PINHOLE {width} {height} {fx} {fy} {cx} {cy}\n")
#
## ----------------------------
## WRITE images.txt
## ----------------------------
#print("Writing images.txt")
#
#image_files = sorted(os.listdir(image_folder))
#
#with open(os.path.join(output_dir,"images.txt"),"w") as f:
#
#    for i,(q,t) in enumerate(poses):
#
#        if i >= len(image_files):
#            break
#
#        img = image_files[i]
#
#        f.write(
#            f"{i+1} {q[3]} {q[0]} {q[1]} {q[2]} "
#            f"{t[0]} {t[1]} {t[2]} 1 {img}\n\n"
#        )
#
## ----------------------------
## WRITE points3D.txt
## ----------------------------
#print("Writing points3D.txt")
#
#with open(os.path.join(output_dir,"points3D.txt"),"w") as f:
#
#    for i,p in enumerate(points):
#
#        f.write(
#            f"{i} {p[0]} {p[1]} {p[2]} "
#            f"255 255 255 1\n"
#        )
#
#print("\nConversion finished")
#print("Output saved to:",output_dir)
#import os
#import numpy as np
#import trimesh
#from scipy.spatial.transform import Rotation as R
#
## -------------------------
## PATHS
## -------------------------
#scene_path = "/home/mantavya23311/backend_app/reconstruction/tmp459w8g9f_scene.glb"
#image_folder = "/home/mantavya23311/gaussian-splatting/data/bottle/images"
#output_dir = "/home/mantavya23311/gaussian-splatting/data/bottle/sparse/0"
#
#os.makedirs(output_dir, exist_ok=True)
#
## -------------------------
## CAMERA INTRINSICS
## -------------------------
#width = 512
#height = 384
#fx = fy = 500
#cx = width / 2
#cy = height / 2
#
## -------------------------
## LOAD SCENE
## -------------------------
#print("Loading MASt3R scene...")
#scene = trimesh.load(scene_path)
#
## -------------------------
## EXTRACT POINT CLOUD
## -------------------------
#points = []
#colors = []
#
#for geom in scene.geometry.values():
#
#    if hasattr(geom, "vertices"):
#        verts = np.asarray(geom.vertices)
#
#        if hasattr(geom.visual, "vertex_colors"):
#            col = np.asarray(geom.visual.vertex_colors)[:, :3]
#        else:
#            col = np.ones((len(verts), 3)) * 255
#
#        points.append(verts)
#        colors.append(col)
#
#points = np.concatenate(points)
#colors = np.concatenate(colors)
#
#print("Total points:", len(points))
#
## -------------------------
## DOWNSAMPLE
## -------------------------
#max_points = 200000
#
#if len(points) > max_points:
#    idx = np.random.choice(len(points), max_points, replace=False)
#    points = points[idx]
#    colors = colors[idx]
#
#print("Using points:", len(points))
#
## -------------------------
## WRITE cameras.txt
## -------------------------
#print("Writing cameras.txt")
#
#with open(os.path.join(output_dir, "cameras.txt"), "w") as f:
#    f.write("# Camera list\n")
#    f.write("# CAMERA_ID MODEL WIDTH HEIGHT PARAMS\n")
#    f.write(f"1 PINHOLE {width} {height} {fx} {fy} {cx} {cy}\n")
#
## -------------------------
## EXTRACT CAMERA POSES
## -------------------------
#print("Extracting camera poses...")
#
#camera_nodes = []
#
#for node_name in scene.graph.nodes_geometry:
#    transform, geom = scene.graph[node_name]
#    camera_nodes.append((node_name, transform))
#
#print("Found cameras:", len(camera_nodes))
#
## -------------------------
## WRITE images.txt
## -------------------------
#print("Writing images.txt")
#
#image_files = sorted(os.listdir(image_folder))
#
#with open(os.path.join(output_dir, "images.txt"), "w") as f:
#
#    for i, (node, T) in enumerate(camera_nodes):
#
#        if i >= len(image_files):
#            break
#
#        R_wc = T[:3, :3]
#        t_wc = T[:3, 3]
#
#        rot = R.from_matrix(R_wc)
#        q = rot.as_quat()
#
#        qw = q[3]
#        qx = q[0]
#        qy = q[1]
#        qz = q[2]
#
#        tx, ty, tz = t_wc
#
#        img_name = image_files[i]
#
#        f.write(
#            f"{i+1} {qw} {qx} {qy} {qz} "
#            f"{tx} {ty} {tz} 1 {img_name}\n"
#        )
#
#        f.write("\n")
#
## -------------------------
## WRITE points3D.txt
## -------------------------
#print("Writing points3D.txt")
#
#with open(os.path.join(output_dir, "points3D.txt"), "w") as f:
#
#    for i, p in enumerate(points):
#
#        r, g, b = colors[i]
#
#        f.write(
#            f"{i+1} {p[0]} {p[1]} {p[2]} "
#            f"{int(r)} {int(g)} {int(b)} 1\n"
#        )
#
#print("\nDataset conversion finished.")
#print("Saved to:", output_dir)
#import os
#import torch
#import numpy as np
#from scipy.spatial.transform import Rotation as R
#
## -------------------------
## PATHS
## -------------------------
#
#cache_dir = "/home/mantavya23311/backend_app/reconstruction/cache/canon_views"
#image_dir = "/home/mantavya23311/gaussian-splatting/data/bottle/images"
#output_dir = "/home/mantavya23311/gaussian-splatting/data/bottle/sparse/0"
#
#os.makedirs(output_dir, exist_ok=True)
#
## -------------------------
## CAMERA INTRINSICS
## -------------------------
#
#width = 512
#height = 384
#fx = fy = 500
#cx = width/2
#cy = height/2
#
## -------------------------
## WRITE cameras.txt
## -------------------------
#
#with open(os.path.join(output_dir,"cameras.txt"),"w") as f:
#
#    f.write("# Camera list\n")
#    f.write("# CAMERA_ID MODEL WIDTH HEIGHT PARAMS\n")
#    f.write(f"1 PINHOLE {width} {height} {fx} {fy} {cx} {cy}\n")
#
## -------------------------
## LOAD MAST3R POSES
## -------------------------
#
#pose_files = sorted([f for f in os.listdir(cache_dir) if f.endswith(".pth")])
#
#image_files = sorted(os.listdir(image_dir))
#
#print("pose files:",len(pose_files))
#print("images:",len(image_files))
#
#poses = []
#
#for pf in pose_files:
#
#    data = torch.load(os.path.join(cache_dir,pf),map_location="cpu")
#
#    # typical mast3r key
#    if "camera_pose" in data:
#        T = data["camera_pose"]
#
#    elif "extrinsics" in data:
#        T = data["extrinsics"]
#
#    elif "pose" in data:
#        T = data["pose"]
#
#    else:
#        continue
#
#    T = T.numpy()
#    poses.append(T)
#
#print("valid poses:",len(poses))
#
## -------------------------
## WRITE images.txt
## -------------------------
#
#with open(os.path.join(output_dir,"images.txt"),"w") as f:
#
#    for i,(pose,img) in enumerate(zip(poses,image_files)):
#
#        R_wc = pose[:3,:3]
#        t_wc = pose[:3,3]
#
#        rot = R.from_matrix(R_wc)
#        q = rot.as_quat()
#
#        qw = q[3]
#        qx = q[0]
#        qy = q[1]
#        qz = q[2]
#
#        tx,ty,tz = t_wc
#
#        f.write(
#            f"{i+1} {qw} {qx} {qy} {qz} "
#            f"{tx} {ty} {tz} 1 {img}\n"
#        )
#
#        f.write("\n")
#
#print("images.txt written")
#import os
#import torch
#import numpy as np
#from scipy.spatial.transform import Rotation as R
#
#cache_dir = "/home/mantavya23311/backend_app/reconstruction/cache/canon_views"
#image_dir = "/home/mantavya23311/gaussian-splatting/data/bottle/images"
#output_dir = "/home/mantavya23311/gaussian-splatting/data/bottle/sparse/0"
#
#os.makedirs(output_dir, exist_ok=True)
#
#pose_files = sorted([f for f in os.listdir(cache_dir) if f.endswith(".pth")])
#image_files = sorted(os.listdir(image_dir))
#
#print("pose files:",len(pose_files))
#print("images:",len(image_files))
#
## ---------------------
## write cameras.txt
## ---------------------
#
#width = 512
#height = 384
#fx = fy = 500
#cx = width/2
#cy = height/2
#
#with open(os.path.join(output_dir,"cameras.txt"),"w") as f:
#    f.write(f"1 PINHOLE {width} {height} {fx} {fy} {cx} {cy}\n")
#
## ---------------------
## write images.txt
## ---------------------
#
#with open(os.path.join(output_dir,"images.txt"),"w") as f:
#
#    for i,(pf,img) in enumerate(zip(pose_files,image_files)):
#
#        data = torch.load(os.path.join(cache_dir,pf),map_location="cpu")
#
#        params = data[1].numpy()
#
#        rvec = params[0:3]
#        t = params[3:6]
#
#        rot = R.from_rotvec(rvec)
#        q = rot.as_quat()
#
#        qw = q[3]
#        qx = q[0]
#        qy = q[1]
#        qz = q[2]
#
#        tx,ty,tz = t
#
#        f.write(
#            f"{i+1} {qw} {qx} {qy} {qz} "
#            f"{tx} {ty} {tz} 1 {img}\n\n"
#        )
#
#print("images.txt written with real MASt3R poses")
import os
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as R

scene_path = "/home/mantavya23311/backend_app/reconstruction/tmp459w8g9f_scene.glb"

image_dir = "/home/mantavya23311/gaussian-splatting/data/bottle/images"
output_dir = "/home/mantavya23311/gaussian-splatting/data/bottle/sparse/0"

os.makedirs(output_dir, exist_ok=True)

print("Loading MASt3R scene...")
scene = trimesh.load(scene_path)

image_files = sorted(os.listdir(image_dir))

# ---------- Extract points ----------
points = []

for geom in scene.geometry.values():
    if hasattr(geom, "vertices"):
        points.append(np.asarray(geom.vertices))

points = np.concatenate(points)


sample = 200000

if len(points) > sample:
    idx = np.random.choice(len(points), sample, replace=False)
    points = points[idx]
# ---------- Extract cameras ----------
cameras = []

for node in scene.graph.nodes:

    transform, geometry = scene.graph[node]

    if transform is None:
        continue

    if isinstance(transform, np.ndarray) and transform.shape == (4,4):
        cameras.append(transform)

print("points:",len(points))
print("cameras:",len(cameras))

# 🔎 DEBUG CHECK
print("\nFirst few camera matrices:\n")
for i in range(min(5,len(cameras))):
    print(cameras[i])
# ------------------------
# write cameras.txt
# ------------------------

width = 512
height = 384
fx = fy = 500
cx = width/2
cy = height/2

with open(os.path.join(output_dir,"cameras.txt"),"w") as f:
    f.write(f"1 PINHOLE {width} {height} {fx} {fy} {cx} {cy}\n")

# ------------------------
# write images.txt
# ------------------------

with open(os.path.join(output_dir,"images.txt"),"w") as f:

    for i,img in enumerate(image_files):

        if i < len(cameras):

            T = cameras[i]

            Rm = T[:3,:3]
            t = T[:3,3]

        else:
            Rm = np.eye(3)
            t = np.zeros(3)

        q = R.from_matrix(Rm).as_quat()

        qw,qx,qy,qz = q[3],q[0],q[1],q[2]

        f.write(
            f"{i+1} {qw} {qx} {qy} {qz} "
            f"{t[0]} {t[1]} {t[2]} 1 {img}\n\n"
        )
# ------------------------
# write points3D.txt
# ------------------------

with open(os.path.join(output_dir,"points3D.txt"),"w") as f:

    for i,p in enumerate(points):

        f.write(
            f"{i} {p[0]} {p[1]} {p[2]} 255 255 255 1\n"
        )

print("COLMAP dataset generated")
print("images:",len(image_files))
print("cameras:",len(cameras))
