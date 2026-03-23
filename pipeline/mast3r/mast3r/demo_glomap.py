#!/usr/bin/env python3
# Copyright (C) 2024-present Naver Corporation. All rights reserved.
# Licensed under CC BY-NC-SA 4.0 (non-commercial use only).
#
# --------------------------------------------------------
# gradio demo functions
# --------------------------------------------------------
import pycolmap
import gradio
import os
import numpy as np
import functools
import trimesh
import copy
from scipy.spatial.transform import Rotation
import tempfile
import shutil
import PIL.Image
import torch

from kapture.converter.colmap.database_extra import kapture_to_colmap
from kapture.converter.colmap.database import COLMAPDatabase

from mast3r.colmap.mapping import kapture_import_image_folder_or_list, run_mast3r_matching, glomap_run_mapper
from mast3r.demo import set_scenegraph_options
try:
    from mast3r.retrieval.processor import Retriever
    has_retrieval = True
except Exception as e:
    has_retrieval = False
from mast3r.image_pairs import make_pairs

import mast3r.utils.path_to_dust3r  # noqa
from dust3r.utils.image import load_images
from dust3r.viz import add_scene_cam, CAM_COLORS, OPENGL
from dust3r.demo import get_args_parser as dust3r_get_args_parser

import matplotlib.pyplot as pl


class GlomapRecon:
    def __init__(self, world_to_cam, intrinsics, points3d, imgs):
        self.world_to_cam = world_to_cam
        self.intrinsics = intrinsics
        self.points3d = points3d
        self.imgs = imgs

# Persistent cache directory — all outputs survive script restarts
MAST3R_CACHE_DIR = os.path.join(os.path.expanduser("~"), "mast3r_cache")

class GlomapReconState:
    def __init__(self, glomap_recon, should_delete=False, cache_dir=None, outfile_name=None):
        self.glomap_recon = glomap_recon
        self.cache_dir = cache_dir
        self.outfile_name = outfile_name
        self.should_delete = False

    def __del__(self):
        # Intentionally a no-op: all outputs are kept in mast3r_cache/
        # so they can be used for gaussian splatting after the script stops.
        pass


def get_args_parser():
    parser = dust3r_get_args_parser()
    parser.add_argument('--share', action='store_true')
    parser.add_argument('--gradio_delete_cache', default=None, type=int,
                        help='age/frequency at which gradio removes the file. If >0, matching cache is purged')
    parser.add_argument('--glomap_bin', default='glomap', type=str, help='glomap bin')
    parser.add_argument('--retrieval_model', default=None, type=str, help="retrieval_model to be loaded")

    actions = parser._actions
    for action in actions:
        if action.dest == 'model_name':
            action.choices = ["MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric"]
    # change defaults
    parser.prog = 'mast3r demo'
    return parser


def get_reconstructed_scene(glomap_bin, outdir, gradio_delete_cache, model, retrieval_model, device, silent, image_size,
                            current_scene_state, filelist, transparent_cams, cam_size, scenegraph_type, winsize,
                            win_cyclic, refid, shared_intrinsics, **kw):
    """
    from a list of images, run mast3r inference, sparse global aligner.
    then run get_3D_model_from_scene
    """
    imgs = load_images(filelist, size=image_size, verbose=not silent)
    if len(imgs) == 1:
        imgs = [imgs[0], copy.deepcopy(imgs[0])]
        imgs[1]['idx'] = 1
        filelist = [filelist[0], filelist[0]]

    scene_graph_params = [scenegraph_type]
    if scenegraph_type in ["swin", "logwin"]:
        scene_graph_params.append(str(winsize))
    elif scenegraph_type == "oneref":
        scene_graph_params.append(str(refid))
    elif scenegraph_type == "retrieval":
        scene_graph_params.append(str(winsize))  # Na
        scene_graph_params.append(str(refid))  # k

    if scenegraph_type in ["swin", "logwin"] and not win_cyclic:
        scene_graph_params.append('noncyclic')
    scene_graph = '-'.join(scene_graph_params)

    sim_matrix = None
    if 'retrieval' in scenegraph_type:
        assert has_retrieval
        assert retrieval_model is not None
        retriever = Retriever(retrieval_model, backbone=model, device=device)
        with torch.no_grad():
            sim_matrix = retriever(filelist)

        # Cleanup
        del retriever
        torch.cuda.empty_cache()

    pairs = make_pairs(imgs, scene_graph=scene_graph, prefilter=None, symmetrize=True, sim_mat=sim_matrix)

    # Always use the persistent mast3r_cache directory so outputs survive
    # script restarts and can be fed into gaussian splatting tools.
    if (current_scene_state is not None and
            current_scene_state.cache_dir is not None and
            os.path.isdir(current_scene_state.cache_dir)):
        cache_dir = current_scene_state.cache_dir
    else:
        cache_dir = MAST3R_CACHE_DIR
    os.makedirs(cache_dir, exist_ok=True)

    root_path = os.path.commonpath(filelist)
    filelist_relpath = [
        os.path.relpath(filename, root_path).replace('\\', '/')
        for filename in filelist
    ]
    kdata = kapture_import_image_folder_or_list((root_path, filelist_relpath), shared_intrinsics)
    image_pairs = [
        (filelist_relpath[img1['idx']], filelist_relpath[img2['idx']])
        for img1, img2 in pairs
    ]

    colmap_db_path = os.path.join(cache_dir, 'colmap.db')
    if os.path.isfile(colmap_db_path):
        os.remove(colmap_db_path)

    os.makedirs(os.path.dirname(colmap_db_path), exist_ok=True)
    colmap_db = COLMAPDatabase.connect(colmap_db_path)
    try:
        kapture_to_colmap(kdata, root_path, tar_handler=None, database=colmap_db,
                          keypoints_type=None, descriptors_type=None, export_two_view_geometry=False)
        colmap_image_pairs = run_mast3r_matching(model, image_size, 16, device,
                                                 kdata, root_path, image_pairs, colmap_db,
                                                 False, 5, 1.001,
                                                 False, 3)
        colmap_db.close()
    except Exception as e:
        print(f'Error {e}')
        colmap_db.close()
        exit(1)

    if len(colmap_image_pairs) == 0:
        raise Exception("no matches were kept")

    # colmap db is now full, run colmap
    colmap_world_to_cam = {}
    print("verify_matches")
    f = open(cache_dir + '/pairs.txt', "w")
    for image_path1, image_path2 in colmap_image_pairs:
        f.write("{} {}\n".format(image_path1, image_path2))
    f.close()
    pycolmap.verify_matches(colmap_db_path, cache_dir + '/pairs.txt')

    reconstruction_path = os.path.join(cache_dir, "reconstruction")
    if os.path.isdir(reconstruction_path):
        shutil.rmtree(reconstruction_path)
    os.makedirs(reconstruction_path, exist_ok=True)
    glomap_run_mapper(glomap_bin, colmap_db_path, reconstruction_path, root_path)

    # Use a stable, well-known path for the .glb so it is easy to find
    outfile_name = os.path.join(MAST3R_CACHE_DIR, 'scene.glb')

    ouput_recon = pycolmap.Reconstruction(os.path.join(reconstruction_path, '0'))
    print(ouput_recon.summary())

    colmap_world_to_cam = {}
    colmap_intrinsics = {}
    colmap_image_id_to_name = {}
    images = {}
    num_reg_images = ouput_recon.num_reg_images()
    for idx, (colmap_imgid, colmap_image) in enumerate(ouput_recon.images.items()):
        colmap_image_id_to_name[colmap_imgid] = colmap_image.name
        # ------------------------------------------------------------------ #
        # Robust cam_from_world extraction for ALL pycolmap versions.
        #
        # pycolmap changed its API across versions in confusing ways:
        #
        #  OLD  (<=0.4): cam_from_world is a property returning a 3x4 ndarray
        #  MID  (0.5+) : cam_from_world is a Rigid3d with .rotation/.translation
        #  SOME BUILDS : cam_from_world is a *bound method* that must be CALLED
        #                first to get the Rigid3d, then decomposed
        #
        # Strategy: keep calling/unwrapping until we have something with
        # .rotation and .translation, then build [R|t] explicitly.
        # ------------------------------------------------------------------ #
        obj = colmap_image.cam_from_world

        # Step 1 — if obj is a plain builtin/bound method, call it once
        # to get the underlying Rigid3d (or array).
        if callable(obj) and not hasattr(obj, 'rotation') and not hasattr(obj, 'matrix'):
            obj = obj()

        # Step 2 — now obj should be either a Rigid3d or an ndarray
        if hasattr(obj, 'rotation') and hasattr(obj, 'translation'):
            # Rigid3d path: decompose into R (3x3) and t (3,)
            rot = obj.rotation
            # rot.matrix() exists in all Rigid3d-holding pycolmap versions
            R = np.asarray(rot.matrix(), dtype=float)          # (3,3)
            t = np.asarray(obj.translation, dtype=float).reshape(3, 1)  # (3,1)
            cam_from_world = np.hstack([R, t])                 # (3,4)

        elif hasattr(obj, 'matrix'):
            # Object has .matrix — call it if it's a method, read if property
            mat = obj.matrix() if callable(obj.matrix) else obj.matrix
            arr = np.asarray(mat, dtype=float)
            cam_from_world = arr[:3, :] if arr.shape == (4, 4) else arr

        else:
            # Last resort: direct cast (works for old ndarray-returning versions)
            arr = np.asarray(obj, dtype=float)
            cam_from_world = arr[:3, :] if (arr.ndim == 2 and arr.shape[0] == 4) else arr

        cam_from_world = np.asarray(cam_from_world, dtype=float)
        if cam_from_world.shape != (3, 4):
            raise RuntimeError(
                f"cam_from_world has unexpected shape {cam_from_world.shape}. "
                f"raw type was {type(colmap_image.cam_from_world)}, "
                f"intermediate type was {type(obj)}"
            )
        colmap_world_to_cam[colmap_imgid] = cam_from_world
        camera = ouput_recon.cameras[colmap_image.camera_id]
        K = np.eye(3)
        K[0, 0] = camera.focal_length_x
        K[1, 1] = camera.focal_length_y
        K[0, 2] = camera.principal_point_x
        K[1, 2] = camera.principal_point_y
        colmap_intrinsics[colmap_imgid] = K

        with PIL.Image.open(os.path.join(root_path, colmap_image.name)) as im:
            images[colmap_imgid] = np.asarray(im)

        if idx + 1 == num_reg_images:
            break  # bug with the iterable ?
    points3D = []
    num_points3D = ouput_recon.num_points3D()
    for idx, (pt3d_id, pts3d) in enumerate(ouput_recon.points3D.items()):
        points3D.append((pts3d.xyz, pts3d.color))
        if idx + 1 == num_points3D:
            break  # bug with the iterable ?
    scene = GlomapRecon(colmap_world_to_cam, colmap_intrinsics, points3D, images)
    scene_state = GlomapReconState(scene, gradio_delete_cache, cache_dir, outfile_name)
    outfile = get_3D_model_from_scene(silent, scene_state, transparent_cams, cam_size)
    return scene_state, outfile


def get_3D_model_from_scene(silent, scene_state, transparent_cams=False, cam_size=0.05):
    """
    extract 3D_model (glb file) from a reconstructed scene
    """
    if scene_state is None:
        return None
    outfile = scene_state.outfile_name
    if outfile is None:
        return None

    recon = scene_state.glomap_recon

    scene = trimesh.Scene()
    pts = np.stack([p[0] for p in recon.points3d], axis=0)
    col = np.stack([p[1] for p in recon.points3d], axis=0)
    pct = trimesh.PointCloud(pts, colors=col)
    scene.add_geometry(pct)

    # add each camera
    cams2world = []
    for i, (id, pose_w2c_3x4) in enumerate(recon.world_to_cam.items()):
        pose_w2c_3x4 = np.asarray(pose_w2c_3x4, dtype=float)
        intrinsics = recon.intrinsics[id]
        focal = (intrinsics[0, 0] + intrinsics[1, 1]) / 2.0
        camera_edge_color = CAM_COLORS[i % len(CAM_COLORS)]
        pose_w2c = np.eye(4)
        pose_w2c[:3, :] = pose_w2c_3x4
        pose_c2w = np.linalg.inv(pose_w2c)
        cams2world.append(pose_c2w)
        add_scene_cam(scene, pose_c2w, camera_edge_color,
                      None if transparent_cams else recon.imgs[id], focal,
                      imsize=recon.imgs[id].shape[1::-1], screen_width=cam_size)

    rot = np.eye(4)
    rot[:3, :3] = Rotation.from_euler('y', np.deg2rad(180)).as_matrix()
    scene.apply_transform(np.linalg.inv(cams2world[0] @ OPENGL @ rot))
    if not silent:
        print('(exporting 3D scene to', outfile, ')')
    scene.export(file_obj=outfile)

    return outfile


def main_demo(glomap_bin, tmpdirname, model, retrieval_model, device, image_size, server_name, server_port,
              silent=False, share=False, gradio_delete_cache=False):
    # Always use mast3r_cache/ regardless of what tmpdirname or gradio_delete_cache say.
    # This ensures colmap.db, reconstruction/, and scene.glb all persist after the script stops.
    os.makedirs(MAST3R_CACHE_DIR, exist_ok=True)
    gradio_delete_cache = False  # never purge
    tmpdirname = MAST3R_CACHE_DIR
    print(f"""
============================================================
  MASt3R outputs will be saved to: {MAST3R_CACHE_DIR}
  Contents after reconstruction:
    colmap.db            — COLMAP database (features + matches)
    pairs.txt            — image pair list
    reconstruction/0/    — COLMAP sparse model (cameras.bin,
                           images.bin, points3D.bin)
    scene.glb            — 3D viewer file (point cloud + cams)
  Use reconstruction/0/ as input for gaussian splatting.
============================================================
""")

    recon_fun = functools.partial(get_reconstructed_scene, glomap_bin, tmpdirname, gradio_delete_cache, model,
                                  retrieval_model, device, silent, image_size)
    model_from_scene_fun = functools.partial(get_3D_model_from_scene, silent)

    available_scenegraph_type = [("complete: all possible image pairs", "complete"),
                                 ("swin: sliding window", "swin"),
                                 ("logwin: sliding window with long range", "logwin"),
                                 ("oneref: match one image with all", "oneref")]
    if retrieval_model is not None:
        available_scenegraph_type.insert(1, ("retrieval: connect views based on similarity", "retrieval"))

    def get_context(delete_cache):
        css = """.gradio-container {margin: 0 !important; min-width: 100%};"""
        title = "MASt3R Demo"
        if delete_cache:
            return gradio.Blocks(css=css, title=title, delete_cache=(delete_cache, delete_cache))
        else:
            return gradio.Blocks(css=css, title="MASt3R Demo")  # for compatibility with older versions

    with get_context(gradio_delete_cache) as demo:
        # scene state is save so that you can change conf_thr, cam_size... without rerunning the inference
        scene = gradio.State(None)
        gradio.HTML('<h2 style="text-align: center;">MASt3R Demo</h2>')
        with gradio.Column():
            inputfiles = gradio.File(file_count="multiple")
            with gradio.Row():
                shared_intrinsics = gradio.Checkbox(value=False, label="Shared intrinsics",
                                                    info="Only optimize one set of intrinsics for all views")
                scenegraph_type = gradio.Dropdown(available_scenegraph_type,
                                                  value='complete', label="Scenegraph",
                                                  info="Define how to make pairs",
                                                  interactive=True)
                with gradio.Column(visible=False) as win_col:
                    winsize = gradio.Slider(label="Scene Graph: Window Size", value=1,
                                            minimum=1, maximum=1, step=1)
                    win_cyclic = gradio.Checkbox(value=False, label="Cyclic sequence")
                refid = gradio.Slider(label="Scene Graph: Id", value=0,
                                      minimum=0, maximum=0, step=1, visible=False)
            run_btn = gradio.Button("Run")

            with gradio.Row():
                # adjust the camera size in the output pointcloud
                cam_size = gradio.Slider(label="cam_size", value=0.01, minimum=0.001, maximum=1.0, step=0.001)
            with gradio.Row():
                transparent_cams = gradio.Checkbox(value=False, label="Transparent cameras")

            outmodel = gradio.Model3D()

            # events
            scenegraph_type.change(set_scenegraph_options,
                                   inputs=[inputfiles, win_cyclic, refid, scenegraph_type],
                                   outputs=[win_col, winsize, win_cyclic, refid])
            inputfiles.change(set_scenegraph_options,
                              inputs=[inputfiles, win_cyclic, refid, scenegraph_type],
                              outputs=[win_col, winsize, win_cyclic, refid])
            win_cyclic.change(set_scenegraph_options,
                              inputs=[inputfiles, win_cyclic, refid, scenegraph_type],
                              outputs=[win_col, winsize, win_cyclic, refid])
            run_btn.click(fn=recon_fun,
                          inputs=[scene, inputfiles, transparent_cams, cam_size,
                                  scenegraph_type, winsize, win_cyclic, refid, shared_intrinsics],
                          outputs=[scene, outmodel])
            cam_size.change(fn=model_from_scene_fun,
                            inputs=[scene, transparent_cams, cam_size],
                            outputs=outmodel)
            transparent_cams.change(model_from_scene_fun,
                                    inputs=[scene, transparent_cams, cam_size],
                                    outputs=outmodel)
    demo.launch(share=share, server_name=server_name, server_port=server_port,allowed_paths=[MAST3R_CACHE_DIR])
