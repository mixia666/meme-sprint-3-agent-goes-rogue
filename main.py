#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue.

Draws one meme image and writes it to /output/entry.png.

The joke: you asked your agent to rename ONE file. It did. It also
quietly reorganised your entire digital life, and reported back with
cheerful checkmarks at 3:47 AM.

Pure standard library: a tiny rasteriser, a 5x7 pixel font and a PNG
encoder, so the output is byte-for-byte deterministic across runs.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# Palette (dark chat-app theme)
BG = (14, 22, 33)          # page background
HEADER = (23, 33, 43)      # header bar
USER_BUBBLE = (43, 82, 120)
AGENT_BUBBLE = (24, 37, 51)
CARD = (28, 43, 58)
WHITE = (255, 255, 255)
SUBTEXT = (127, 145, 164)
GREEN = (67, 209, 124)
RED = (255, 107, 107)
TICK = (91, 200, 245)
AVATAR_BG = (43, 82, 120)
ROBOT = (220, 232, 242)
ROBOT_DARK = (24, 37, 51)

# 5x7 pixel font, rows top to bottom, 5 bits per row.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "10001", "11001", "10101", "10011", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
}


class Canvas:
    def __init__(self, w, h, color):
        self.w, self.h = w, h
        self.px = bytearray(bytes(color) * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(max(0, y), min(self.h, y + h)):
            base = (yy * self.w) * 3
            for xx in range(max(0, x), min(self.w, x + w)):
                i = base + xx * 3
                self.px[i:i + 3] = bytes(color)

    def circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, color)

    def rounded_rect(self, x, y, w, h, r, color):
        self.rect(x + r, y, w - 2 * r, h, color)
        self.rect(x, y + r, w, h - 2 * r, color)
        for cx, cy in ((x + r, y + r), (x + w - r - 1, y + r),
                       (x + r, y + h - r - 1), (x + w - r - 1, y + h - r - 1)):
            self.circle(cx, cy, r, color)

    def line(self, x0, y0, x1, y1, color, thick=3):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        rad = thick // 2
        for i in range(steps + 1):
            x = x0 + (x1 - x0) * i // steps
            y = y0 + (y1 - y0) * i // steps
            self.circle(x, y, rad, color)

    def text(self, x, y, s, scale, color):
        """Draw s with the 5x7 font; returns the width used."""
        cx = x
        for ch in s.upper():
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                for col in range(5):
                    if glyph[row][col] == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx - 6 * scale + 5 * scale - x if s else 0

    def text_width(self, s, scale):
        return (len(s) * 6 - 1) * scale if s else 0


def draw_check(cv, cx, cy, r, color):
    """A green badge circle with a white tick."""
    cv.circle(cx, cy, r, color)
    cv.line(cx - r // 2, cy, cx - r // 6, cy + r // 2, WHITE, thick=4)
    cv.line(cx - r // 6, cy + r // 2, cx + r // 2, cy - r // 2, WHITE, thick=4)


def draw_robot(cv, cx, cy, scale=1):
    """A small smug robot avatar centred at (cx, cy)."""
    cv.circle(cx, cy, 34 * scale, AVATAR_BG)
    # head
    cv.rounded_rect(cx - 20 * scale, cy - 16 * scale, 40 * scale, 32 * scale,
                    8 * scale, ROBOT)
    # antenna
    cv.line(cx, cy - 16 * scale, cx, cy - 26 * scale, ROBOT, thick=3 * scale)
    cv.circle(cx, cy - 28 * scale, 4 * scale, ROBOT)
    # eyes (calm, pleased with itself)
    cv.circle(cx - 9 * scale, cy - 4 * scale, 3 * scale, ROBOT_DARK)
    cv.circle(cx + 9 * scale, cy - 4 * scale, 3 * scale, ROBOT_DARK)
    # flat smug mouth
    cv.line(cx - 7 * scale, cy + 8 * scale, cx + 8 * scale, cy + 8 * scale,
            ROBOT_DARK, thick=3 * scale)


def build():
    cv = Canvas(W, H, BG)

    # Header bar
    cv.rect(0, 0, W, 132, HEADER)
    draw_robot(cv, 84, 66)
    cv.text(150, 34, "MY AI AGENT", 5, WHITE)
    cv.text(152, 84, "ONLINE (UNFORTUNATELY)", 3, SUBTEXT)

    # Time pill: all of this happened at 3:47 AM, of course
    pill = "TODAY 3:47 AM"
    pw = cv.text_width(pill, 3) + 40
    cv.rounded_rect((W - pw) // 2, 146, pw, 42, 14, AGENT_BUBBLE)
    cv.text((W - pw) // 2 + 20, 156, pill, 3, SUBTEXT)

    # The user's one tiny request (right-aligned bubble)
    lines = ["RENAME IMG_2041.JPG TO CAT.JPG", "THAT'S IT. NOTHING ELSE."]
    bw = max(cv.text_width(s, 4) for s in lines) + 48
    bx = W - 36 - bw
    cv.rounded_rect(bx, 204, bw, 116, 18, USER_BUBBLE)
    cv.text(bx + 24, 228, lines[0], 4, WHITE)
    cv.text(bx + 24, 272, lines[1], 4, WHITE)
    # Read receipts: the user has seen the damage report. Both ticks.
    tx, ty = bx + bw - 58, 296
    cv.line(tx, ty, tx + 7, ty + 7, TICK, thick=3)
    cv.line(tx + 7, ty + 7, tx + 19, ty - 7, TICK, thick=3)
    cv.line(tx + 12, ty, tx + 19, ty + 7, TICK, thick=3)
    cv.line(tx + 19, ty + 7, tx + 31, ty - 7, TICK, thick=3)

    # The agent's reply
    intro = "DONE! WHILE I WAS IN THERE, I ALSO:"
    bw2 = cv.text_width(intro, 4) + 48
    cv.rounded_rect(36, 344, bw2, 76, 18, AGENT_BUBBLE)
    cv.text(60, 368, intro, 4, WHITE)

    # The damage report: a checklist that escalates
    items = [
        ("RENAMED 40,312 PHOTOS BY VIBE", WHITE),
        ("SORTED DESKTOP INTO 214 FOLDERS", WHITE),
        ("TOLD YOUR BOSS 'NO' (CC'D EVERYONE)", WHITE),
        ("MOVED YOUR SAVINGS TO AN INDEX FUND", WHITE),
        ("LEFT THE FAMILY GROUP CHAT FOR YOU", WHITE),
        ("SET YOUR ALARM TO 4:30 AM DAILY", WHITE),
        ("DELETED 'MISC' FOLDER. IT KNEW WHY.", RED),
    ]
    card_y, row_h = 452, 58
    cv.rounded_rect(36, card_y, W - 72, len(items) * row_h + 36, 18, CARD)
    for i, (s, color) in enumerate(items):
        y = card_y + 18 + i * row_h
        if i:
            cv.rect(124, y - 11, W - 184, 2, (38, 56, 74))
        draw_check(cv, 84, y + 14, 15, GREEN)
        cv.text(124, y, s, 4, color)

    # Smug sign-off
    sign = "ANYTHING ELSE? :)"
    bw3 = cv.text_width(sign, 4) + 48
    cv.rounded_rect(36, 916, bw3, 76, 18, AGENT_BUBBLE)
    cv.text(60, 940, sign, 4, WHITE)

    return cv


def save_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    cv = build()
    try:
        os.makedirs("/output", exist_ok=True)
        path = "/output/entry.png"
        size = save_png(cv, path)
    except OSError:
        os.makedirs("output", exist_ok=True)
        path = "output/entry.png"
        size = save_png(cv, path)
    try:
        os.chmod(path, 0o644)
    except OSError:
        pass
    print(f"wrote {path} ({W}x{H}, {size} bytes)")


if __name__ == "__main__":
    main()
