import torch
from pathlib import Path

from mast3r.model import AsymmetricMASt3R
from mast3r.image_pairs import make_pairs
from mast3r.fast_nn import fast_reciprocal_NNs

from dust3r.utils.image import load_images
from dust3r.inference import inference


# ---------------- SETTINGS ---------------- #

images_dir = "/home/mantavya23311/backend_app/uploads/bottle_test"
weights = "/home/mantavya23311/mast3r/checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth"

device = "cuda"
chunk_size = 20

# ------------------------------------------ #

print("Loading images...")
imgs = load_images(images_dir, size=512)

print("Loading MASt3R model...")
model = AsymmetricMASt3R.from_pretrained(weights).to(device).eval()

print("Generating pairs...")
pairs = make_pairs(imgs, scene_graph="complete")
print("Total pairs:", len(pairs))

output_dir = Path("mast3r_matches")
output_dir.mkdir(exist_ok=True)

all_matches = []

for i in range(0, len(pairs), chunk_size):

    chunk = pairs[i:i+chunk_size]

    print(f"\nProcessing chunk {i//chunk_size + 1}")

    with torch.no_grad():

        output = inference(
            chunk,
            model,
            device=device,
            batch_size=1,
            verbose=True
        )

    desc1 = output["pred1"]["desc"]
    desc2 = output["pred2"]["desc"]

    conf1 = output["pred1"]["conf"]
    conf2 = output["pred2"]["conf"]

    B = desc1.shape[0]

    for b in range(B):

        matches = fast_reciprocal_NNs(
            desc1[b],
            desc2[b],
            conf1[b],
            conf2[b]
        )

        all_matches.append(matches)

    del output
    torch.cuda.empty_cache()


print("\nSaving matches...")

torch.save(all_matches, output_dir / "matches.pt")

print("Done.")
print("Matches saved in:", output_dir)
