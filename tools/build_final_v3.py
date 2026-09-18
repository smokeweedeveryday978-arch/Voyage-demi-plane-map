from __future__ import annotations

import json
import shutil
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work_final_v3"
OUT = ROOT / "final_v3"
MASTER_DIR = OUT / "master"
TILES_DIR = OUT / "tiles"

NAMES = {
    1:"The_Dim_March", 2:"The_Grey_Boundary", 3:"The_Open_Horizon", 4:"The_Fade", 5:"The_Last_Edge",
    6:"The_Low_Reaches", 7:"The_Hollow_Vale", 8:"The_Deep_Expanse", 9:"The_Southroll", 10:"The_Rift_March",
    11:"The_Quiet_Shore", 12:"The_Westreach", 13:"Heartgate_Basin", 14:"The_Dawn_Barrow", 15:"The_Easthold",
    16:"Veiled_Fox_Sanctuary", 17:"The_First_Meadow", 18:"The_Threshold_March", 19:"The_Stone_Rise", 20:"The_Mirror_Mere",
    21:"The_Still_Frontier", 22:"The_Pale_Reaches", 23:"The_North_Field", 24:"The_Fold", 25:"The_Veiled_Edge",
}

COORDS = {
    1:(-2,-8), 2:(-1,-8), 3:(0,-8), 4:(1,-8), 5:(2,-8),
    6:(-2,-9), 7:(-1,-9), 8:(0,-9), 9:(1,-9), 10:(2,-9),
    11:(-2,-10), 12:(-1,-10), 13:(0,-10), 14:(1,-10), 15:(2,-10),
    16:(-2,-11), 17:(-1,-11), 18:(0,-11), 19:(1,-11), 20:(2,-11),
    21:(-2,-12), 22:(-1,-12), 23:(0,-12), 24:(1,-12), 25:(2,-12),
}

def find_source() -> Path:
    candidates = [
        WORK / "realesrgan" / "master_source_out.png",
        WORK / "realesrgan" / "master_source.png",
        WORK / "realesrgan" / "master_source.jpg",
        WORK / "master_source.jpg",
    ]
    for p in candidates:
        if p.exists():
            return p
    folder = WORK / "realesrgan"
    if folder.exists():
        found = sorted(folder.glob("master_source*"))
        if found:
            return found[0]
    raise FileNotFoundError("No final v3 master source found")

def prepare_master(src: Path) -> Image.Image:
    im = Image.open(src).convert("RGB")
    side = min(im.width, im.height)
    left = (im.width - side) // 2
    top = (im.height - side) // 2
    im = im.crop((left, top, left + side, top + side))

    target = 12000
    if im.size != (target, target):
        im = im.resize((target, target), Image.Resampling.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=0.7, percent=55, threshold=2))
    return im

def save_master(im: Image.Image) -> tuple[Path, int]:
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    out = MASTER_DIR / "master_map_12000px.jpg"
    for q in (98, 97, 96, 95, 94, 93, 92):
        im.save(out, "JPEG", quality=q, subsampling=0, optimize=True, progressive=True)
        if out.stat().st_size < 94 * 1024 * 1024:
            return out, q
    return out, 92

def export_tiles(im: Image.Image) -> None:
    if TILES_DIR.exists():
        shutil.rmtree(TILES_DIR)
    TILES_DIR.mkdir(parents=True, exist_ok=True)

    tile_px = im.width // 5
    if im.width != im.height or tile_px * 5 != im.width:
        raise RuntimeError(f"Master must be square and divisible by 5, got {im.size}")

    owner = "smokeweedeveryday978-arch"
    repo = "Voyage-demi-plane-map"
    base = f"https://raw.githubusercontent.com/{owner}/{repo}/main/final_v3"

    manifest = {
        "version": "final_v3",
        "orientation": "01 TOP-LEFT -> 25 BOTTOM-RIGHT, left-to-right then top-to-bottom",
        "master_dimensions": [im.width, im.height],
        "tile_dimensions": [tile_px, tile_px],
        "grid_top_to_bottom": [
            ["01","02","03","04","05"],
            ["06","07","08","09","10"],
            ["11","12","13","14","15"],
            ["16","17","18","19","20"],
            ["21","22","23","24","25"],
        ],
        "grid_regions_top_to_bottom": [
            ["The Dim March","The Grey Boundary","The Open Horizon","The Fade","The Last Edge"],
            ["The Low Reaches","The Hollow Vale","The Deep Expanse","The Southroll","The Rift March"],
            ["The Quiet Shore","The Westreach","Heartgate Basin","The Dawn Barrow","The Easthold"],
            ["Veiled Fox Sanctuary","The First Meadow","The Threshold March","The Stone Rise","The Mirror Mere"],
            ["The Still Frontier","The Pale Reaches","The North Field","The Fold","The Veiled Edge"],
        ],
        "master_url": f"{base}/master/master_map_12000px.jpg",
        "regions": []
    }

    for n in range(1, 26):
        row = (n - 1) // 5
        col = (n - 1) % 5
        box = (col*tile_px, row*tile_px, (col+1)*tile_px, (row+1)*tile_px)
        tile = im.crop(box)

        filename = f"{n:02d}_{NAMES[n]}.jpg"
        out = TILES_DIR / filename
        tile.save(out, "JPEG", quality=100, subsampling=0, optimize=True, progressive=True)

        x, y = COORDS[n]
        manifest["regions"].append({
            "tile": f"{n:02d}",
            "region": NAMES[n].replace("_", " "),
            "coordinates": {"x": x, "y": y},
            "file": filename,
            "url": f"{base}/tiles/{filename}",
        })

    (OUT / "voyage_links.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

def main() -> None:
    src = find_source()
    im = prepare_master(src)
    master_path, q = save_master(im)
    export_tiles(im)
    print(f"source={src}")
    print(f"master={master_path} size={im.size} quality={q}")
    print("Final mapping:")
    print("01 02 03 04 05")
    print("06 07 08 09 10")
    print("11 12 13 14 15")
    print("16 17 18 19 20")
    print("21 22 23 24 25")
    print("13 = Heartgate Basin; 16 = Veiled Fox Sanctuary")

if __name__ == "__main__":
    main()
