#!/usr/bin/env python3
"""
Generate a simple, meaningful icon for the Video Annotation Tool.

This script uses Pillow to draw a stylized film strip + waveform + speech bubble
that reflects: video stimulus, audio/linguistic elicitation, and annotation.

It writes a large PNG (1024x1024) and a multi-size ICO for Windows.

Run: python3 scripts/generate_icon.py
"""
from PIL import Image, ImageDraw, ImageFilter
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')
os.makedirs(OUT_DIR, exist_ok=True)

def rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)

def make_icon(path_png, path_ico):
    size = 1024
    img = Image.new('RGBA', (size, size), (30, 60, 80, 255))
    draw = ImageDraw.Draw(img)

    # subtle gradient
    for i in range(size):
        alpha = int(15 * (i/size))
        draw.line([(0, i), (size, i)], fill=(30+alpha, 60+alpha//2, 80+alpha//3, 255))

    padding = 80
    # film strip rounded rectangle
    film_xy = (padding, padding, size-padding, size-padding)
    rounded_rect(draw, film_xy, radius=60, fill=(245, 245, 250, 255))

    # film holes (on left and right)
    hole_w = 36
    hole_sp = 120
    for side_x in (padding + 10, size - padding - 10 - hole_w):
        y = padding + 40
        while y < size - padding - 40:
            draw.rectangle([side_x, y, side_x + hole_w, y + 60], fill=(30, 60, 80, 255))
            y += hole_sp

    # frames inside film
    frame_margin = 28
    inner = (padding + frame_margin, padding + frame_margin, size - padding - frame_margin, size - padding - frame_margin)
    fx0, fy0, fx1, fy1 = inner
    # draw three vertical frames
    fw = (fx1 - fx0) // 3 - 20
    for i in range(3):
        x0 = fx0 + i * (fw + 30)
        y0 = fy0
        x1 = x0 + fw
        y1 = fy1
        draw.rectangle([x0, y0, x1, y1], fill=(230, 240, 250, 255))
        # small inner content placeholder
        cx0 = x0 + 18
        cy0 = y0 + 60
        cx1 = x1 - 18
        cy1 = y1 - 60
        draw.rectangle([cx0, cy0, cx1, cy1], fill=(200, 220, 235, 255))

    # waveform across the center frame to indicate audio/linguistics
    import math
    wf_y = (fy0 + fy1) // 2
    wf_x0 = fx0 + 18
    wf_x1 = fx1 - 18
    amp = 40
    points = []
    for xi in range(wf_x0, wf_x1, 6):
        t = (xi - wf_x0) / (wf_x1 - wf_x0) * 4 * math.pi
        y = wf_y + int(math.sin(t) * amp * (1 + 0.3*math.cos(0.5*t)))
        points.append((xi, y))
    draw.line(points, fill=(200, 60, 60, 255), width=12)

    # speech bubble overlay at top-right
    sb_w = 260
    sb_h = 180
    sb_x = fx1 - sb_w - 30
    sb_y = fy0 + 30
    draw.rounded_rectangle([sb_x, sb_y, sb_x+sb_w, sb_y+sb_h], radius=30, fill=(255,255,255,230))
    # tail
    tail = [(sb_x+40, sb_y+sb_h-10), (sb_x+20, sb_y+sb_h+30), (sb_x+90, sb_y+sb_h-10)]
    draw.polygon(tail, fill=(255,255,255,230))
    # small lines inside bubble
    draw.line([(sb_x+30, sb_y+50), (sb_x+sb_w-30, sb_y+50)], fill=(30,60,80,255), width=10)
    draw.line([(sb_x+30, sb_y+90), (sb_x+sb_w-100, sb_y+90)], fill=(30,60,80,255), width=10)

    # subtle shadow
    shadow = img.filter(ImageFilter.GaussianBlur(radius=2))
    img = Image.alpha_composite(shadow, img)

    # write PNG
    png_path = path_png
    img.convert('RGBA').save(png_path)
    print('Wrote', png_path)

    # create ICO with common sizes
    sizes = [(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)]
    icons = [img.resize(s, Image.LANCZOS).convert('RGBA') for s in sizes]
    # Pillow supports saving a single image with sizes parameter
    ico_path = path_ico
    img.save(ico_path, sizes=[s for s in sizes])
    print('Wrote', ico_path)

if __name__ == '__main__':
    png = os.path.join(OUT_DIR, 'icon.png')
    ico = os.path.join(OUT_DIR, 'icon.ico')
    make_icon(png, ico)
