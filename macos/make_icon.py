"""Zeichnet das Grauzone-Icon (1024 x 1024 PNG) mit Pillow.

Aufruf:  python make_icon.py ausgabe.png
Motiv:   Dokument mit geschwärzten Zeilen und Schutzschild auf dunkelgrauem Grund.
"""
import sys
from PIL import Image, ImageDraw, ImageFilter

S = 4                      # Supersampling für glatte Kanten
N = 1024 * S


def p(v):
    return int(v * S)


def verlauf(w, h, oben, unten):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(oben, unten)))
    return img


def main(ziel):
    icon = Image.new("RGBA", (N, N), (0, 0, 0, 0))

    # Grundfläche im macOS-Raster (824 px, Rand 100 px), leichter Schatten
    schatten = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(schatten).rounded_rectangle(
        [p(100), p(112), p(924), p(936)], radius=p(185), fill=(0, 0, 0, 90))
    icon.alpha_composite(schatten.filter(ImageFilter.GaussianBlur(p(14))))

    maske = Image.new("L", (N, N), 0)
    ImageDraw.Draw(maske).rounded_rectangle([p(100), p(100), p(924), p(924)], radius=p(185), fill=255)
    grund = verlauf(N, N, (74, 85, 104), (31, 37, 48)).convert("RGBA")
    icon.paste(grund, (0, 0), maske)

    d = ImageDraw.Draw(icon)

    # Dokument mit Eselsohr
    x0, y0, x1, y1, ohr = 262, 205, 742, 820, 110
    blatt_schatten = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(blatt_schatten).polygon(
        [(p(x0), p(y0 + 14)), (p(x1 - ohr), p(y0 + 14)), (p(x1), p(y0 + ohr + 14)),
         (p(x1), p(y1 + 14)), (p(x0), p(y1 + 14))], fill=(0, 0, 0, 110))
    icon.alpha_composite(blatt_schatten.filter(ImageFilter.GaussianBlur(p(16))))
    d = ImageDraw.Draw(icon)
    d.polygon([(p(x0), p(y0)), (p(x1 - ohr), p(y0)), (p(x1), p(y0 + ohr)),
               (p(x1), p(y1)), (p(x0), p(y1))], fill=(248, 249, 251))
    d.polygon([(p(x1 - ohr), p(y0)), (p(x1 - ohr), p(y0 + ohr)), (p(x1), p(y0 + ohr))],
              fill=(208, 214, 223))

    # Zeilen: (Länge, geschwärzt?)
    zeilen = [(300, False), (360, True), (390, False), (250, True),
              (380, False), (330, False), (210, True)]
    y = 300
    for laenge, schwarz in zeilen:
        if schwarz:
            d.rounded_rectangle([p(318), p(y - 8), p(318 + laenge), p(y + 34)],
                                radius=p(8), fill=(24, 27, 33))
        else:
            d.rounded_rectangle([p(318), p(y + 4), p(318 + laenge), p(y + 22)],
                                radius=p(9), fill=(196, 202, 212))
        y += 64

    # Schutzschild unten rechts
    cx, cy, b, h = 708, 742, 230, 262
    schild = [
        (cx - b / 2, cy - h / 2 + 30), (cx, cy - h / 2), (cx + b / 2, cy - h / 2 + 30),
        (cx + b / 2, cy + 10), (cx + b / 2 - 20, cy + 60), (cx, cy + h / 2),
        (cx - b / 2 + 20, cy + 60), (cx - b / 2, cy + 10),
    ]
    rand = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(rand).polygon([(p(x), p(yy + 10)) for x, yy in schild], fill=(0, 0, 0, 120))
    icon.alpha_composite(rand.filter(ImageFilter.GaussianBlur(p(12))))
    d = ImageDraw.Draw(icon)
    d.polygon([(p(x), p(yy)) for x, yy in schild], fill=(255, 255, 255))
    innen = [(cx + (x - cx) * 0.86, cy + (yy - cy) * 0.86) for x, yy in schild]
    d.polygon([(p(x), p(yy)) for x, yy in innen], fill=(34, 160, 132))
    d.line([(p(cx - 52), p(cy + 2)), (p(cx - 12), p(cy + 44)), (p(cx + 58), p(cy - 44))],
           fill=(255, 255, 255), width=p(28), joint="curve")

    icon.resize((1024, 1024), Image.LANCZOS).save(ziel)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "icon_1024.png")
