import torch

def get_device():
    """
    Returns the best available device: 'mps' for Mac, 'cuda' for Windows/NVIDIA, and 'cpu' as fallback.
    """
    if torch.backends.mps.is_available():
        print("Using Apple Silicon GPU (MPS)")
        return torch.device("mps")
    elif torch.cuda.is_available():
        print("Using NVIDIA GPU (CUDA)")
        return torch.device("cuda")
    else:
        print("Using CPU (Warning: This will be very slow)")
        return torch.device("cpu")

if __name__ == "__main__":
    device = get_device()
    print(f"Selected device: {device}")
