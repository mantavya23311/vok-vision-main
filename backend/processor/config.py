import os
from device import get_device

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Engines
MAST3R_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../pipeline/mast3r"))
GAUSSIAN_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../pipeline/gaussian-splatting"))
OPENSPLAT_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../pipeline/opensplat/build/opensplat"))

# Storage
UPLOAD_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../storage/uploads"))
OUTPUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../storage/outputs"))
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Settings
DEVICE = get_device()
IMAGE_SIZE = (1024, 768)
ITERATIONS = 30000 # Professional quality (30K = industry standard for 3DGS)
BACKEND_URL = os.getenv("BACKEND_URL", "http://192.168.200.84:3000/api/v1")

