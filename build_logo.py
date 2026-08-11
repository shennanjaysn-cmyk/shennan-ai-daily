# -*- coding: utf-8 -*-
"""Build a web-sized PNG logo from the master brand asset.

Reads the master logo PNG (e.g. from the brand asset folder) and writes a
compressed, resized copy under dist/logo.png for deployment. The source SVG
is intentionally NOT published to protect the vector original.
"""
from pathlib import Path
from PIL import Image

BASE = Path(__file__).resolve().parent
DIST = BASE / "dist"
DIST.mkdir(exist_ok=True)

# Source master PNG (kept in project root, NOT committed as SVG)
SRC = BASE / "SN_logo-2.png"
WEB_MAX = 256  # displayed at ~44px; max dimension, keep aspect ratio
OUT = DIST / "logo.png"


def main():
    if not SRC.exists():
        raise FileNotFoundError(f"Logo source not found: {SRC}")

    with Image.open(SRC) as im:
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        # Keep aspect ratio; set the longer side to WEB_MAX
        w, h = im.size
        ratio = min(WEB_MAX / w, WEB_MAX / h)
        new_size = (int(w * ratio), int(h * ratio))
        im_resized = im.resize(new_size, Image.LANCZOS)
        # Optimize PNG; reduce palette is not used to keep the gradient smooth
        im_resized.save(OUT, "PNG", optimize=True)

    print(f"Logo built: {OUT} ({OUT.stat().st_size / 1024:.1f} KB), size {im_resized.size}")


if __name__ == "__main__":
    main()
