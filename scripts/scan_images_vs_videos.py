#!/usr/bin/env python3
import os
import sys
from typing import List, Tuple

IMAGE_EXTS = {".jpg", ".jpeg"}

def list_videos(folder: str) -> List[str]:
    try:
        return sorted([
            f for f in os.listdir(folder)
            if not f.startswith('.') and f.lower().endswith('.mpg') and os.path.isfile(os.path.join(folder, f))
        ])
    except Exception:
        return []

def list_images(folder: str) -> List[Tuple[str, str]]:
    """Return [(name, fullpath)] for images in top-level and common subfolders (images/Images)."""
    out: List[Tuple[str, str]] = []
    try:
        for name in os.listdir(folder):
            full = os.path.join(folder, name)
            if name.startswith('.'):
                continue
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in IMAGE_EXTS:
                out.append((name, full))
    except Exception:
        pass
    for sub in ("images", "Images"):
        subpath = os.path.join(folder, sub)
        if os.path.isdir(subpath):
            try:
                for name in os.listdir(subpath):
                    full = os.path.join(subpath, name)
                    if name.startswith('.'):
                        continue
                    if os.path.isfile(full) and os.path.splitext(name)[1].lower() in IMAGE_EXTS:
                        out.append((name, full))
            except Exception:
                pass
    out.sort(key=lambda t: t[0])
    return out

def basename_no_ext(name: str) -> str:
    n = os.path.splitext(name)[0]
    return n

def scan_folder(folder: str) -> str:
    videos = list_videos(folder)
    images = list_images(folder)
    v_bases = {basename_no_ext(v).lower() for v in videos}
    i_bases = {basename_no_ext(i[0]).lower() for i in images}
    unmatched_videos = sorted([v for v in videos if basename_no_ext(v).lower() not in i_bases])
    unmatched_images = sorted([i for (i, _) in images if basename_no_ext(i).lower() not in v_bases])
    first4_jpgs = [name for (name, _) in images[:4]]
    first4_mpgs = videos[:4]
    lines = []
    lines.append(f"Folder: {folder}")
    lines.append(f"  MPG count: {len(videos)}")
    lines.append(f"  JPG count: {len(images)}")
    lines.append(f"  Matches: {len(v_bases & i_bases)}")
    lines.append(f"  Unmatched MPG (no JPG): {len(unmatched_videos)}")
    if unmatched_videos:
        lines.append(f"    - {', '.join(unmatched_videos[:10])}{' ...' if len(unmatched_videos) > 10 else ''}")
    lines.append(f"  Unmatched JPG (no MPG): {len(unmatched_images)}")
    if unmatched_images:
        lines.append(f"    - {', '.join(unmatched_images[:10])}{' ...' if len(unmatched_images) > 10 else ''}")
    lines.append(f"  First 4 JPGs (sorted): {', '.join(first4_jpgs) if first4_jpgs else 'None'}")
    lines.append(f"  First 4 MPGs (sorted): {', '.join(first4_mpgs) if first4_mpgs else 'None'}")
    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print("Usage: scan_images_vs_videos.py <folder1> [<folder2> ...]")
        sys.exit(1)
    for folder in sys.argv[1:]:
        print(scan_folder(folder))
        print("")

if __name__ == "__main__":
    main()