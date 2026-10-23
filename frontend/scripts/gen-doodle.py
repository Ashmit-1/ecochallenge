#!/usr/bin/env python3
"""Generate the eco-doodle wallpaper tile used as the page background (design.md §3).

Prints the CSS declaration to paste into src/styles/index.css:

    --field-doodle: url("data:image/svg+xml,...");

With --preview PATH it also writes an .svg preview (3x2 tiles on paper)
for visual inspection:  python3 scripts/gen-doodle.py --preview /tmp/doodle.svg

The tile is 300x300 and fully self-contained (no elements cross the edges),
so background-repeat tiles seamlessly. When changing artwork, keep:
  - stroke #2F6B4F (moss) at stroke-opacity 0.14 (WhatsApp-like softness)
  - hand-drawn feel: 1.7px round-cap strokes, organic rotations
  - all motifs fully inside the tile
"""
import argparse
import math
from urllib.parse import quote

STROKE = "#2F6B4F"
OPACITY = "0.14"
WIDTH = 1.7
TILE = 300


def pt(cx, cy, a_deg, r):
    a = math.radians(a_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def fmt(p):
    return f"{p[0]:.1f} {p[1]:.1f}"


def build() -> str:
    parts = []

    # seedling / sprout
    parts.append(
        '<g transform="translate(-118,-104) rotate(-8)">'
        '<path d="M0 22 C0 8 0 -2 -3 -14"/>'
        '<path d="M-1 8 C-13 6 -18 -4 -12 -14 C-5 -9 -1 1 -1 8 Z"/>'
        '<path d="M-2 -6 C9 -9 15 -19 10 -27 C3 -23 0 -14 -2 -6 Z"/>'
        "</g>"
    )

    # recycle: triangle of chasing arrows, computed so arrowheads stay symmetric
    cx, cy, R = 0.0, 0.0, 15
    verts = [pt(cx, cy, -90 + i * 120, R) for i in range(3)]
    seg = []
    for i in range(3):
        S, T = verts[i], verts[(i + 1) % 3]
        vx, vy = T[0] - S[0], T[1] - S[1]
        L = math.hypot(vx, vy)
        ux, uy = vx / L, vy / L
        A = (S[0] + ux * L * 0.16, S[1] + uy * L * 0.16)
        B = (S[0] + ux * L * 0.86, S[1] + uy * L * 0.86)
        base = (B[0] - ux * 5, B[1] - uy * 5)
        px, py = -uy * 3.2, ux * 3.2
        b1 = (base[0] + px, base[1] + py)
        b2 = (base[0] - px, base[1] - py)
        seg.append(f'<path d="M{fmt(A)} L{fmt(B)}"/>')
        seg.append(f'<path d="M{fmt(B)} L{fmt(b1)} M{fmt(B)} L{fmt(b2)}"/>')
    parts.append('<g transform="translate(2,-110) rotate(4)">' + "".join(seg) + "</g>")

    # leaf with veins
    parts.append(
        '<g transform="translate(90,-80) rotate(14)">'
        '<path d="M0 0 C6 -16 22 -26 36 -28 C33 -12 20 4 2 4 Z"/>'
        '<path d="M3 3 C12 -8 24 -18 34 -25"/>'
        '<path d="M11 -4 L14 -12 M19 -11 L21 -18"/>'
        "</g>"
    )

    # sun
    rays = []
    for k in range(8):
        a = k * 45
        p1 = pt(0, 0, a, 11)
        p2 = pt(0, 0, a, 16)
        rays.append(f'<path d="M{fmt(p1)} L{fmt(p2)}"/>')
    parts.append(
        '<g transform="translate(-120,-8)"><circle cx="0" cy="0" r="7"/>'
        + "".join(rays)
        + "</g>"
    )

    # water droplet
    parts.append(
        '<g transform="translate(-8,-6) rotate(6)">'
        '<path d="M0 -14 C7 -4 11 1 11 6 A11 11 0 0 1 -11 6 C-11 1 -7 -4 0 -14 Z"/>'
        '<path d="M-5 8 A5 5 0 0 0 1 10"/>'
        "</g>"
    )

    # bicycle
    parts.append(
        '<g transform="translate(112,8) rotate(-4)">'
        '<circle cx="-13" cy="6" r="9"/><circle cx="13" cy="6" r="9"/>'
        '<path d="M-13 6 L-4 -6 L 8 6 M-4 -6 L 1 6 M-13 6 L 6 6"/>'
        '<path d="M-4 -6 L-8 -10 M8 6 L6 -8 L10 -9"/>'
        "</g>"
    )

    # tree
    parts.append(
        '<g transform="translate(-108,102) rotate(3)">'
        '<path d="M0 20 L0 4"/><path d="M0 10 L-7 5 M0 13 L6 9"/>'
        '<circle cx="0" cy="-6" r="12"/>'
        "</g>"
    )

    # globe
    parts.append(
        '<g transform="translate(8,112) rotate(-6)">'
        '<circle cx="0" cy="0" r="13"/>'
        '<ellipse cx="0" cy="0" rx="5.5" ry="13"/>'
        '<path d="M-13 0 L13 0"/>'
        "</g>"
    )

    # potted seedling
    parts.append(
        '<g transform="translate(110,112) rotate(5)">'
        '<path d="M-9 2 L9 2 L6 14 L-6 14 Z"/>'
        '<path d="M0 2 L0 -6"/>'
        '<path d="M0 -2 C-8 -4 -11 -11 -7 -16 C-2 -12 0 -6 0 -2 Z"/>'
        '<path d="M0 -8 C7 -10 11 -16 8 -21 C3 -18 1 -12 0 -8 Z"/>'
        "</g>"
    )

    # small leaf fillers
    parts.append(
        '<g transform="translate(-58,58) rotate(-24)">'
        '<path d="M0 0 C4 -10 14 -16 22 -17 C20 -7 12 3 0 3 Z"/></g>'
    )
    parts.append(
        '<g transform="translate(-52,-52) rotate(130)">'
        '<path d="M0 0 C4 -10 14 -16 22 -17 C20 -7 12 3 0 3 Z"/></g>'
    )

    body = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TILE} {TILE}" '
        f'width="{TILE}" height="{TILE}">'
        f'<g fill="none" stroke="{STROKE}" stroke-opacity="{OPACITY}" stroke-width="{WIDTH}" '
        f'stroke-linecap="round" stroke-linejoin="round" transform="translate({TILE // 2},{TILE // 2})">'
        f"{body}</g></svg>"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", help="write an SVG preview (3x2 tiles on paper) here")
    args = parser.parse_args()

    svg = build()
    if args.preview:
        preview = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{TILE * 3}" height="{TILE * 2}">'
            f'<rect width="100%" height="100%" fill="#F7F5EE"/>'
            + "".join(
                f'<svg x="{c * TILE}" y="{r * TILE}" width="{TILE}" height="{TILE}">{svg}</svg>'
                for r in range(2)
                for c in range(3)
            )
            + "</svg>"
        )
        with open(args.preview, "w", encoding="utf-8") as f:
            f.write(preview)
        print(f"preview: {args.preview}", flush=True)

    encoded = quote(svg, safe="/:.,-()= ")
    print(f'--field-doodle: url("data:image/svg+xml,{encoded}");')


if __name__ == "__main__":
    main()