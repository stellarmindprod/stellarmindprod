from PIL import Image
import os

d = 'static/images'
for f in os.listdir(d):
    if f.endswith('.jpg') or f.endswith('.png'):
        try:
            img = Image.open(os.path.join(d, f))
            print(f"{f}: {img.size}")
        except Exception as e:
            print(f"{f}: {e}")
