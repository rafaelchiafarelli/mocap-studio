"""Labelled grid of feature renders: python contact_sheet.py IN_DIR OUT.png COLUMNS [suffix]"""
import glob, os, sys
from PIL import Image, ImageDraw


def main(d, out, cols, suffix="f"):
    cols = int(cols)
    paths = sorted(glob.glob(f"{d}/*_{suffix}.png"))
    w, h = Image.open(paths[0]).size
    h += 26
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), "white")
    for i, p in enumerate(paths):
        tile = Image.open(p).convert("RGB")
        x, y = (i % cols) * w, (i // cols) * h
        sheet.paste(tile, (x, y + 26))
        ImageDraw.Draw(sheet).text((x + 8, y + 6), os.path.basename(p).rsplit("_", 1)[0].lstrip("_"), fill="black")
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main(*sys.argv[1:])
