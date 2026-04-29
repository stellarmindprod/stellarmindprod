import os
import struct

def get_image_info():
    d = 'static/images'
    for f in os.listdir(d):
        path = os.path.join(d, f)
        if f.endswith('.png'):
            with open(path, 'rb') as img:
                head = img.read(24)
                if head[:8] == b'\x89PNG\r\n\x1a\n':
                    w, h = struct.unpack('>LL', head[16:24])
                    print(f"{f}: {w}x{h} (Aspect Ratio: {w/h:.2f})")
        elif f.endswith('.jpg') or f.endswith('.jpeg'):
            # Just print the size
            print(f"{f}: JPEG Size={os.path.getsize(path)} bytes")

get_image_info()
