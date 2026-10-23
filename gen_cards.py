# -*- coding: utf-8 -*-
"""生成传统正规扑克牌面 PNG（白底、红黑花色、左上/右下索引、中央大花色）
输出到 cards/ 目录，命名 {s}{r}.png；s=c(梅花)/h(红桃)/s(黑桃)/d(方块)"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cards")
W, H = 160, 224

SUITS = [("d", "\u2666", (214, 40, 40)),   # 方块 红
         ("h", "\u2665", (214, 40, 40)),   # 红桃 红
         ("s", "\u2660", (28, 28, 32)),    # 黑桃 黑
         ("c", "\u2663", (28, 28, 32))]    # 梅花 黑

RANKS = ["4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "3"]

FONT_IDX = "C:/Windows/Fonts/arialbd.ttf"
FONT_BIG = "C:/Windows/Fonts/arialbd.ttf"


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def text_w(draw, txt, font):
    b = draw.textbbox((0, 0), txt, font=font)
    return b[2] - b[0], b[3] - b[1]


def draw_card(rank, suit_ch, color, name):
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    # 圆角白底 + 细边框
    r = 18
    d.rounded_rectangle([1, 1, W - 2, H - 2], radius=r, fill=(255, 255, 255, 255),
                        outline=(60, 60, 70), width=2)
    f_idx = load_font(FONT_IDX, 30)
    f_small = load_font(FONT_IDX, 22)
    f_big = load_font(FONT_BIG, 88)
    # 左上角索引
    d.text((12, 6), rank, font=f_idx, fill=color)
    d.text((15, 42), suit_ch, font=f_small, fill=color)
    # 右下角索引（旋转 180°）
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dt = ImageDraw.Draw(tmp)
    dt.text((12, 6), rank, font=f_idx, fill=color)
    dt.text((15, 42), suit_ch, font=f_small, fill=color)
    tmp = tmp.rotate(180, expand=False)
    mask = tmp.split()[3]
    img.paste(tmp, (0, 0), mask)
    # 中央大花色
    w, h = text_w(d, suit_ch, f_big)
    d.text(((W - w) / 2 + 12, (H - h) / 2 - 10), suit_ch, font=f_big, fill=color)
    img.save(os.path.join(OUT, name), "PNG")


def draw_back(name="back1.png"):
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([1, 1, W - 2, H - 2], radius=18, fill=(18, 74, 148),
                        outline=(10, 45, 100), width=2)
    # 菱形花纹
    f = load_font(FONT_BIG, 40)
    for y in range(20, H - 20, 48):
        for x in range(20, W - 20, 44):
            d.text((x, y), "\u2666", font=f, fill=(255, 255, 255, 200))
    img.save(os.path.join(OUT, name), "PNG")


def main():
    os.makedirs(OUT, exist_ok=True)
    for s, ch, col in SUITS:
        for r in RANKS:
            draw_card(r, ch, col, "%s%s.png" % (s, r.upper()))
    draw_back("back1.png")
    draw_back("back2.png")
    print("generated %d cards" % (len(SUITS) * len(RANKS) + 2))


if __name__ == "__main__":
    main()