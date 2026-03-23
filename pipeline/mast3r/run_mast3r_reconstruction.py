import os
import numpy as np
import torch
from pathlib import Path

from mast3r.model import AsymmetricMASt3R
from mast3r.image_pairs import make_pairs
from dust3r.utils.image import load_images
from mast3r.fast_nn import fast_reciprocal_NNs
from dust3r.inference import inference

images_dir = "/home/mantavya23311/backend_app/uploads/bottle_test"
weights = "/home/mantavya23311/mast3r/checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth"
device="cuda"
chunk_size=20
print("Loading images...")
imgs = load_images(images_dir, size=512)

print("Loading MASt3R model...")
model = AsymmetricMASt3R.from_pretrained(weights).to("cuda").eval()

print("Generating image pairs...")
pairs = make_pairs(imgs, scene_graph="complete")


print("Total pairs:", len(pairs))


output_dir = Path("mast3r_matches")
output_dir.mkdir(exist_ok=True)

all_matches = []

# Process pairs in chunks
for i in range(0, len(pairs), chunk_size):

    chunk_pairs = pairs[i:i+chunk_size]

    print(f"\nProcessing chunk {i//chunk_size + 1}")
    print(f"Pairs {i} → {i+len(chunk_pairs)-1}")

    with torch.no_grad():
        output = inference(
            chunk_pairs,
            model,
            device=device,
            batch_size=1,
            verbose=True
        )

    print("Extracting matches...")

    desc1_batch = output["pred1"]["desc"]
    desc2_batch = output["pred2"]["desc"]

    conf1_batch = output["pred1"]["conf"]
    conf2_batch = output["pred2"]["conf"]

    B,H,W,D = desc1_batch.shape
    N=H*W

    for b in range(B):

        desc1 = desc1_batch[b].reshape(N,D)
        desc2 = desc2_batch[b].reshape(N,D)

        conf1 = conf1_batch[b].reshape(N)
        conf2 = conf2_batch[b].reshape(N)

        ys, xs = torch.meshgrid(
            torch.arange(H, device=desc1.device),
            torch.arange(W, device=desc1.device),
            indexing="ij"
        )

        xy = torch.stack([xs.reshape(-1), ys.reshape(-1)], dim=1).float()

        xy1 = xy
        xy2 = xy

        matches = fast_reciprocal_NNs(
            desc1,
            desc2,
            xy1,
            xy2,
            conf1,
            conf2
        )

        all_matches.append(matches)

    # Free memory before next chunk
    del output
    torch.cuda.empty_cache()
print("MASt3R matching complete.")

# Save results
output = Path("mast3r_matches")
output.mkdir(exist_ok=True)

torch.save(matches, output / "matches.pt")

print("Matches saved in:", output)
print("Next step: run GLOMAP reconstruction.")
