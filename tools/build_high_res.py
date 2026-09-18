from __future__ import annotations

import json
import os
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "tiles"
WORK = ROOT / "work_high_res"
MASTER_DIR = ROOT / "master"
UPRIGHT_DIR = ROOT / "tiles_v2_upright"
VOYAGE_DIR = ROOT / "tiles_v2_voyage"

NAMES = {
    1:"The_Still_Frontier", 2:"The_Pale_Reaches", 3:"The_North_Field",
    4:"The_Fold", 5:"The_Veiled_Edge", 6:"Veiled_Fox_Sanctuary",
    7:"The_First_Meadow", 8:"The_Threshold_March", 9:"The_Stone_Rise",
    10:"The_Mirror_Mere", 11:"The_Quiet_Shore", 12:"The_Westreach",
    13:"Heartgate_Basin", 14:"The_Dawn_Barrow", 15:"The_Easthold",
    16:"The_Low_Reaches", 17:"The_Hollow_Vale", 18:"The_Deep_Expanse",
    19:"The_Southroll", 20:"The_Rift_March", 21:"The_Dim_March",
    22:"The_Grey_Boundary", 23:"The_Open_Horizon", 24:"The_Fade",
    25:"The_Last_Edge"
}

def src_path(n: int) -> Path:
    return SRC_DIR / f"{n:02d}_{NAMES[n]}.jpg"

def ensure_dirs():
    for d in (WORK, MASTER_DIR, UPRIGHT_DIR, VOYAGE_DIR):
        d.mkdir(parents=True, exist_ok=True)

def assemble_source() -> Path:
    first = Image.open(src_path(1)).convert("RGB")
    tw, th = first.size
    canvas = Image.new("RGB", (tw * 5, th * 5))
    for n in range(1, 26):
        tile = Image.open(src_path(n)).convert("RGB")
        if tile.size != (tw, th):
            raise RuntimeError(f"Tile {n:02d} size {tile.size} != {(tw, th)}")
        col = (n - 1) % 5
        row_from_bottom = (n - 1) // 5
        row_from_top = 4 - row_from_bottom
        canvas.paste(tile, (col * tw, row_from_top * th))
    out = WORK / "master_source.png"
    canvas.save(out, optimize=True)
    print(f"assembled={out} size={canvas.size}")
    return out

def locate_upscaled() -> Path | None:
    candidates = [
        WORK / "realesrgan" / "master_source_out.png",
        WORK / "realesrgan" / "master_source.png",
    ]
    for p in candidates:
        if p.exists():
            return p
    found = list((WORK / "realesrgan").glob("master_source*")) if (WORK / "realesrgan").exists() else []
    return found[0] if found else None

def fallback_upscale(source: Path) -> Path:
    im = Image.open(source).convert("RGB")
    target = (im.width * 4, im.height * 4)
    im = im.resize(target, Image.Resampling.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.15, percent=120, threshold=2))
    out = WORK / "fallback_upscaled.png"
    im.save(out, optimize=True)
    print("WARNING: Real-ESRGAN output missing; used Lanczos fallback")
    return out

def save_master(im: Image.Image):
    # Preserve a huge master while staying below GitHub's 100 MB per-file limit.
    out = MASTER_DIR / f"master_map_{im.width}px.jpg"
    for q in (98, 97, 96, 95, 94, 93, 92):
        im.save(out, "JPEG", quality=q, subsampling=0, optimize=True, progressive=True)
        mb = out.stat().st_size / (1024 * 1024)
        print(f"master JPEG q={q}: {mb:.1f} MB")
        if mb < 94:
            return out, q
    return out, 92

def export(upscaled: Path):
    im = Image.open(upscaled).convert("RGB")
    # Force an exact 5x5 divisible canvas without changing composition.
    side = min(im.width, im.height)
    side -= side % 5
    left = (im.width - side) // 2
    top = (im.height - side) // 2
    im = im.crop((left, top, left + side, top + side))
    tile_px = side // 5

    master_path, master_q = save_master(im)

    # Exact crops from one enhanced master. No independent regeneration = exact seams.
    for n in range(1, 26):
        col = (n - 1) % 5
        row_from_bottom = (n - 1) // 5
        row_from_top = 4 - row_from_bottom
        box = (col * tile_px, row_from_top * tile_px,
               (col + 1) * tile_px, (row_from_top + 1) * tile_px)
        tile = im.crop(box)

        upright = UPRIGHT_DIR / f"{n:02d}_{NAMES[n]}.png"
        tile.save(upright, "PNG", optimize=True, compress_level=7)

        # Voyage displayed the tested tile 180 degrees inverted.
        # Pre-rotate the delivery copy so Voyage's observed rotation restores it.
        voyage = VOYAGE_DIR / f"{n:02d}_{NAMES[n]}.png"
        tile.transpose(Image.Transpose.ROTATE_180).save(
            voyage, "PNG", optimize=True, compress_level=7
        )

    owner = "smokeweedeveryday978-arch"
    repo = "Voyage-demi-plane-map"
    base = f"https://raw.githubusercontent.com/{owner}/{repo}/main"
    manifest = {
        "orientation": [
            [21,22,23,24,25],
            [16,17,18,19,20],
            [11,12,13,14,15],
            [6,7,8,9,10],
            [1,2,3,4,5]
        ],
        "master": f"{base}/master/{master_path.name}",
        "master_dimensions": [side, side],
        "tile_dimensions": [tile_px, tile_px],
        "master_jpeg_quality": master_q,
        "note": "tiles_v2_voyage are pre-rotated 180 degrees to compensate for the Voyage rotation observed by the user. tiles_v2_upright are exact upright crops for reference.",
        "tiles": []
    }
    for n in range(1, 26):
        filename = f"{n:02d}_{NAMES[n]}.png"
        manifest["tiles"].append({
            "number": n,
            "name": NAMES[n].replace("_", " "),
            "voyage_url": f"{base}/tiles_v2_voyage/{filename}",
            "upright_url": f"{base}/tiles_v2_upright/{filename}"
        })
    (ROOT / "voyage_links_v2.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"master": str(master_path), "side": side, "tile_px": tile_px}, indent=2))

def main():
    ensure_dirs()
    source = assemble_source()
    upscaled = locate_upscaled()
    if upscaled is None:
        upscaled = fallback_upscale(source)
    export(upscaled)

if __name__ == "__main__":
    main()
