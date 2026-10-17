"""Fabrique logo, avatar, favicon et illustrations dans public/ (à lancer une fois)."""
import math
import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs("public/avatars", exist_ok=True)
TEAL, DARK, WHITE = (20, 184, 166), (15, 23, 42), (255, 255, 255)


# ------------------------------- images PNG ---------------------------------
def hexagone(d, cx, cy, r, **kw):
    pts = [(cx + r * math.cos(math.radians(60 * i - 30)),
            cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
    d.polygon(pts, **kw)
    return pts


def icone(taille, fond, trait):
    img = Image.new("RGBA", (taille, taille), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if fond:
        d.rounded_rectangle([0, 0, taille - 1, taille - 1], radius=taille // 4, fill=fond)
    c, r = taille / 2, taille * 0.30
    pts = hexagone(d, c, c, r, outline=trait, width=max(2, taille // 28))
    for x, y in pts[::2]:
        d.ellipse([x - taille * .045, y - taille * .045, x + taille * .045, y + taille * .045], fill=trait)
    d.ellipse([c - taille * .06, c - taille * .06, c + taille * .06, c + taille * .06], fill=trait)
    return img


def logo(couleur_texte, nom):
    h = 96
    img = Image.new("RGBA", (330, h), (0, 0, 0, 0))
    img.paste(icone(h, None, TEAL), (0, 0))
    try:
        font = ImageFont.truetype("arialbd.ttf", 44)
    except OSError:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
        except OSError:
            font = ImageFont.load_default()
    ImageDraw.Draw(img).text((h + 6, h // 2 - 26), "ChemAsk", font=font, fill=couleur_texte)
    img.save(nom)


icone(256, TEAL, DARK).save("public/avatars/assistant.png")
icone(64, TEAL, DARK).save("public/favicon.png")
icone(256, None, TEAL).save("public/icone.png")
logo(WHITE, "public/logo_dark.png")
logo(DARK, "public/logo_light.png")


# ----------------------------- illustrations SVG -----------------------------
def hex_pts(cx, cy, r, rot=30):
    return [(cx + r * math.cos(math.radians(60 * i - rot)),
             cy + r * math.sin(math.radians(60 * i - rot))) for i in range(6)]


def molecule(w, h, fond=None, echelle=1.0, decor=26):
    """Deux cycles fusionnés + chaîne latérale + atomes N/O, style structure chimique."""
    r = 46 * echelle
    cx, cy = w * 0.42, h * 0.52
    c2 = (cx + r * math.sqrt(3), cy)
    a, b = hex_pts(cx, cy, r), hex_pts(*c2, r)
    s = []
    if fond:
        s.append(f'<rect width="{w}" height="{h}" fill="{fond}"/>')
    # petits atomes décoratifs
    import random
    rnd = random.Random(7)
    for _ in range(decor):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        s.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rnd.uniform(1.5, 3.5):.1f}" fill="url(#g)" opacity=".55"/>')
    for pts in (a, b):
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        s.append(f'<polygon points="{poly}" fill="none" stroke="url(#g)" stroke-width="3" stroke-linejoin="round"/>')
        for i in (0, 2, 4):  # doubles liaisons (traits intérieurs)
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            mx, my = (pts[0][0] + pts[3][0]) / 2, (pts[0][1] + pts[3][1]) / 2
            k = 0.18
            s.append(f'<line x1="{x1 + (mx - x1) * k:.1f}" y1="{y1 + (my - y1) * k:.1f}" '
                     f'x2="{x2 + (mx - x2) * k:.1f}" y2="{y2 + (my - y2) * k:.1f}" '
                     f'stroke="url(#g)" stroke-width="2" opacity=".7"/>')
    # chaîne latérale : sommet haut-gauche -> N -> chaîne ; sommet bas-droit -> O
    atomes = []
    def chaine(p, dx, dy, labels):
        x0, y0 = p
        pts = [(x0, y0)]
        for k, lab in enumerate(labels):
            x0, y0 = x0 + dx * (1 if k % 2 == 0 else 1), y0 + dy * (1 if k % 2 == 0 else -0.6)
            pts.append((x0, y0))
            atomes.append((x0, y0, lab))
        s.append("<polyline points=\"" + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                 + '" fill="none" stroke="url(#g)" stroke-width="3" stroke-linecap="round"/>')
    chaine(a[4], -34 * echelle, -26 * echelle, ["N", "C", "O"])
    chaine(b[1], 36 * echelle, 24 * echelle, ["N", "S"])
    chaine(b[0], 34 * echelle, -28 * echelle, ["O"])
    for x, y, lab in atomes:
        col = {"N": "#6366f1", "O": "#ef4444", "S": "#eab308", "C": "#14b8a6"}[lab]
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{13 * echelle:.0f}" fill="{col}"/>')
        s.append(f'<text x="{x:.1f}" y="{y + 5 * echelle:.1f}" text-anchor="middle" font-family="Arial,sans-serif" '
                 f'font-weight="700" font-size="{14 * echelle:.0f}" fill="#fff">{lab}</text>')
    defs = ('<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#14b8a6"/><stop offset="1" stop-color="#6366f1"/></linearGradient></defs>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            + defs + "".join(s) + "</svg>")


open("public/hero.svg", "w", encoding="utf-8").write(molecule(520, 230))
open("public/login.svg", "w", encoding="utf-8").write(molecule(1200, 900, fond="#0b1220", echelle=2.2, decor=70))
print("Images créées dans public/")