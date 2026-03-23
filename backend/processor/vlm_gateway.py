import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
from PIL import Image
import dotenv
from pillow_heif import register_heif_opener

register_heif_opener()
dotenv.load_dotenv()

class VLMGateway:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def audit_images(self, image_paths):
        """
        Audits a list of images for quality, blur, and lighting.
        Returns a list of rejected image paths with reasons.
        """
        results = []
        for path in image_paths:
            try:
                img = Image.open(path)
                prompt = "Analyze this image for 3D reconstruction. Is it blurry, poorly lit, or too low resolution? Answer with 'OK' or a brief reason for rejection."
                response = self.model.generate_content([prompt, img])
                if "OK" not in response.text.upper():
                    results.append({"path": path, "reason": response.text.strip()})
            except Exception as e:
                print(f"⚠️ VLM: Failed to process image {os.path.basename(path)}: {e}")
                continue
        return results

    def get_object_mask_hint(self, image_path):
        """
        Asks the VLM to describe the main object and its location to assist masking.
        """
        img = Image.open(image_path)
        prompt = "Identify the main object in this image and describe its bounding box coordinates (ymin, xmin, ymax, xmax) in normalized 0-1000 scale."
        response = self.model.generate_content([prompt, img])
        return response.text.strip()

if __name__ == "__main__":
    # Example usage
    try:
        gateway = VLMGateway()
        print("VLM Gateway Initialized")
    except Exception as e:
        print(f"Error: {e}")
