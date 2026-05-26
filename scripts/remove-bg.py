#!/usr/bin/env python3
"""
Sprite sheet background remover — border flood-fill algorithm.

Removes the background from a grid-based sprite sheet by flood-filling from
the image border outward. Only connected border-touching pixels are removed,
so internal white areas (eyes, markings) are preserved.

Each sprite frame is processed independently so background in one frame
cannot bleed into another.

Usage:
  python3 remove-bg.py <input> <output> [options]

Options:
  --rows N           Number of sprite rows (default: auto-detect)
  --cols N           Number of sprite cols (default: auto-detect)
  --frame-w W        Output frame width in px (default: auto from content)
  --frame-h H        Output frame height in px (default: auto from content)
  --tolerance T      Flood-fill color tolerance 0-255 (default: 28)
  --padding P        Extra padding around content in output frame (default: 10)
  --align ALIGN      Vertical content alignment: 'bottom' or 'center' (default: bottom)

Examples:
  # Auto-detect grid, remove background, output with auto frame size
  python3 remove-bg.py cows.png cows-clean.png

  # Explicit 5x3 grid with 240x220 output frames
  python3 remove-bg.py cows.png cows-clean.png --rows 5 --cols 3 --frame-w 240 --frame-h 220

  # Custom tolerance for images with more varied backgrounds
  python3 remove-bg.py sheep.png sheep-clean.png --rows 3 --cols 4 --tolerance 40
"""

import sys
import argparse
import numpy as np
from PIL import Image
from collections import deque


# ── Flood-fill background removal ────────────────────────────────────────────

def remove_bg_flood_fill(img_rgb: np.ndarray, tolerance: int = 28) -> np.ndarray:
    """
    Remove background from an RGB image using border flood-fill.
    Returns an RGBA array where background pixels have alpha=0.

    Seeds: every pixel on the 4 edges of the image.
    Flood rule: expand to neighbors whose color distance from the seed's
    initial color is within `tolerance` (Euclidean in RGB space).
    """
    h, w = img_rgb.shape[:2]
    alpha = np.ones((h, w), dtype=np.uint8) * 255
    visited = np.zeros((h, w), dtype=bool)

    # Seed color = average of the 4 corner pixels (robust for solid backgrounds)
    corners = [img_rgb[0, 0], img_rgb[0, w-1], img_rgb[h-1, 0], img_rgb[h-1, w-1]]
    bg_color = np.mean(corners, axis=0).astype(float)

    queue = deque()

    def enqueue_border():
        for x in range(w):
            queue.append((0, x))
            queue.append((h-1, x))
        for y in range(1, h-1):
            queue.append((y, 0))
            queue.append((y, w-1))

    enqueue_border()

    while queue:
        y, x = queue.popleft()
        if visited[y, x]:
            continue
        visited[y, x] = True

        pixel = img_rgb[y, x].astype(float)
        dist = float(np.sqrt(np.sum((pixel - bg_color) ** 2)))
        if dist > tolerance:
            continue  # not background — stop expanding here

        alpha[y, x] = 0  # mark as transparent

        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                queue.append((ny, nx))

    rgba = np.dstack([img_rgb, alpha])
    return rgba


# ── Grid auto-detection ───────────────────────────────────────────────────────

def detect_grid(arr: np.ndarray, min_gap: int = 5, threshold: int = 5):
    """
    Auto-detect row/column boundaries in a sprite sheet.
    Returns (row_groups, col_groups) where each group is (start, end) inclusive.
    """
    h, w = arr.shape[:2]

    def find_groups(axis):
        groups = []
        in_content = False
        start = 0
        for i in range(arr.shape[axis]):
            if axis == 0:
                line = arr[i, :, :3]
            else:
                line = arr[:, i, :3]
            non_white = int(np.sum(~np.all(line > 240, axis=-1)))
            if non_white > threshold and not in_content:
                in_content = True
                start = i
            elif non_white <= threshold and in_content:
                in_content = False
                groups.append((start, i - 1))
        if in_content:
            groups.append((start, arr.shape[axis] - 1))
        return groups

    row_groups = find_groups(0)
    col_groups = find_groups(1)

    # Merge spurious 1-px gaps
    def merge_close(groups, gap=min_gap):
        merged = []
        for g in groups:
            if merged and g[0] - merged[-1][1] <= gap:
                merged[-1] = (merged[-1][0], g[1])
            else:
                merged.append(list(g))
        return [tuple(g) for g in merged]

    row_groups = merge_close(row_groups)
    col_groups = merge_close(col_groups)
    return row_groups, col_groups


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remove sprite sheet background via border flood-fill.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="Input sprite sheet (RGB PNG)")
    parser.add_argument("output", help="Output sprite sheet (RGBA PNG)")
    parser.add_argument("--rows", type=int, default=0, help="Number of sprite rows (0=auto)")
    parser.add_argument("--cols", type=int, default=0, help="Number of sprite cols (0=auto)")
    parser.add_argument("--frame-w", type=int, default=0, help="Output frame width px (0=auto)")
    parser.add_argument("--frame-h", type=int, default=0, help="Output frame height px (0=auto)")
    parser.add_argument("--tolerance", type=int, default=28, help="Flood-fill tolerance (default 28)")
    parser.add_argument("--padding", type=int, default=10, help="Padding around content in output frame (default 10)")
    parser.add_argument("--align", choices=["bottom", "center"], default="bottom",
                        help="Vertical alignment in frame (default: bottom)")
    args = parser.parse_args()

    img = Image.open(args.input).convert("RGB")
    arr = np.array(img)
    print(f"Input: {args.input}  size={img.size}  mode={img.mode}")

    # Detect or use explicit grid
    row_groups, col_groups = detect_grid(arr)
    print(f"Auto-detected: {len(row_groups)} rows × {len(col_groups)} cols")

    if args.rows > 0 and args.rows != len(row_groups):
        print(f"  → overriding with --rows {args.rows}")
        # Re-split evenly if forced
    if args.cols > 0 and args.cols != len(col_groups):
        print(f"  → overriding with --cols {args.cols}")

    n_rows = args.rows if args.rows > 0 else len(row_groups)
    n_cols = args.cols if args.cols > 0 else len(col_groups)

    # If explicit rows/cols differ from auto, recompute groups by splitting evenly
    if args.rows > 0 and args.rows != len(row_groups):
        h = arr.shape[0]
        step = h // args.rows
        row_groups = [(i * step, min((i+1) * step - 1, h-1)) for i in range(args.rows)]
    if args.cols > 0 and args.cols != len(col_groups):
        w = arr.shape[1]
        step = w // args.cols
        col_groups = [(i * step, min((i+1) * step - 1, w-1)) for i in range(args.cols)]

    print(f"Using: {n_rows} rows × {n_cols} cols")
    for i, (s, e) in enumerate(row_groups):
        print(f"  row {i}: y={s}-{e} h={e-s+1}")
    for i, (s, e) in enumerate(col_groups):
        print(f"  col {i}: x={s}-{e} w={e-s+1}")

    # ── Process each frame ────────────────────────────────────────────────────
    # Find max content dims across all frames (for auto frame size)
    max_content_w = 0
    max_content_h = 0

    # Store processed frames: frames[row][col] = (rgba_array, content_bounds)
    frames = []
    for ri, (ry0, ry1) in enumerate(row_groups):
        row_frames = []
        for ci, (cx0, cx1) in enumerate(col_groups):
            cell_rgb = arr[ry0:ry1+1, cx0:cx1+1]
            cell_rgba = remove_bg_flood_fill(cell_rgb, args.tolerance)

            # Find content bounds in this frame
            alpha = cell_rgba[:, :, 3]
            rows_with = np.where(alpha.sum(axis=1) > 0)[0]
            cols_with = np.where(alpha.sum(axis=0) > 0)[0]
            if len(rows_with):
                ch = int(rows_with[-1] - rows_with[0] + 1)
                cw = int(cols_with[-1] - cols_with[0] + 1)
                max_content_h = max(max_content_h, ch)
                max_content_w = max(max_content_w, cw)
                bounds = (int(rows_with[0]), int(rows_with[-1]),
                          int(cols_with[0]), int(cols_with[-1]))
            else:
                bounds = None
            row_frames.append((cell_rgba, bounds))
        frames.append(row_frames)

    print(f"\nMax content size across all frames: {max_content_w}w × {max_content_h}h")

    # Determine output frame dimensions
    out_w = args.frame_w if args.frame_w > 0 else max_content_w + args.padding * 2
    out_h = args.frame_h if args.frame_h > 0 else max_content_h + args.padding * 2
    print(f"Output frame size: {out_w}w × {out_h}h")
    print(f"Output sheet size: {out_w * n_cols}w × {out_h * n_rows}h")

    # ── Compose output sheet ───────────────────────────────────────────────────
    out_arr = np.zeros((out_h * n_rows, out_w * n_cols, 4), dtype=np.uint8)

    for ri, row_frames in enumerate(frames):
        for ci, (cell_rgba, bounds) in enumerate(row_frames):
            dst_y0 = ri * out_h
            dst_x0 = ci * out_w

            if bounds is None:
                print(f"  Warning: row {ri} col {ci} is empty, skipping")
                continue

            by0, by1, bx0, bx1 = bounds
            content = cell_rgba[by0:by1+1, bx0:bx1+1]
            ch, cw = content.shape[:2]

            # Horizontal: center
            x_off = (out_w - cw) // 2

            # Vertical: bottom or center
            if args.align == "bottom":
                y_off = out_h - ch
            else:
                y_off = (out_h - ch) // 2

            # Clamp to frame bounds (safety)
            src_y0 = max(0, -y_off)
            src_x0 = max(0, -x_off)
            src_y1 = min(ch, out_h - max(0, y_off))
            src_x1 = min(cw, out_w - max(0, x_off))

            dst_y = dst_y0 + max(0, y_off)
            dst_x = dst_x0 + max(0, x_off)

            out_arr[dst_y:dst_y + (src_y1-src_y0),
                    dst_x:dst_x + (src_x1-src_x0)] = content[src_y0:src_y1, src_x0:src_x1]

            if src_y0 > 0 or src_x0 > 0:
                print(f"  Warning: row {ri} col {ci} content clipped "
                      f"(content {ch}×{cw} → frame {out_h}×{out_w})")

    out_img = Image.fromarray(out_arr, "RGBA")
    out_img.save(args.output)
    print(f"\nSaved: {args.output}  ({out_img.size[0]}×{out_img.size[1]} RGBA)")


if __name__ == "__main__":
    main()
