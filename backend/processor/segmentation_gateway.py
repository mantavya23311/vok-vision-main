import os
from rembg import remove
from PIL import Image
import io

class SegmentationGateway:
    def __init__(self):
        # rembg will download models on first use
        pass

    def segment_images(self, image_paths, output_dir):
        """
        Removes background from images and saves them to output_dir.
        """
        os.makedirs(output_dir, exist_ok=True)
        segmented_paths = []
        
        print(f"✂️ Segmenting {len(image_paths)} images...")
        
        for path in image_paths:
            try:
                name = os.path.basename(path)
                out_path = os.path.join(output_dir, name)
                
                with open(path, 'rb') as i:
                    input_data = i.read()
                    output_data = remove(input_data)
                    
                    # Ensure it's saved as RGB (white background) or RGBA
                    # 3DGS usually prefers RGBA or white background
                    img = Image.open(io.BytesIO(output_data))
                    if img.mode == 'RGBA':
                        # Create a white background image (industry standard for 3DGS)
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        # Paste the image on the background using alpha channel as mask
                        background.paste(img, mask=img.split()[3])
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(out_path)
                    
                segmented_paths.append(out_path)
            except Exception as e:
                print(f"⚠️ Segmentation failed for {path}: {e}")
                # Fallback: copy original if segmentation fails
                import shutil
                shutil.copy(path, out_path)
                segmented_paths.append(out_path)
                
        return segmented_paths
