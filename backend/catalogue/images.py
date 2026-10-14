"""
Images des médicaments.

- `preparer_photo` : redimensionne et compresse une photo envoyée (admin ou import en masse).
- `generer_illustration` : dessine une illustration de boîte quand aucune vraie photo n'est disponible.
"""

import colorsys
import hashlib
import io

from django.core.files.base import ContentFile
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

TAILLE_MAX = 800
QUALITE_WEBP = 80
COTE = 640

POLICE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
POLICE_GRAS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def nom_fichier(medicament):
    """Nom de fichier attendu pour un médicament, ex. « doliprane-500-mg »."""
    return slugify(f"{medicament.nom_commercial} {medicament.dosage}")


def preparer_photo(fichier, nom):
    """Photo quelconque → WebP léger (≤ 800 px), orientation corrigée, fond blanc si transparence."""
    image = Image.open(fichier)
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        fond = Image.new("RGB", image.size, "white")
        fond.paste(image, mask=image.getchannel("A"))
        image = fond
    else:
        image = image.convert("RGB")
    image.thumbnail((TAILLE_MAX, TAILLE_MAX), Image.LANCZOS)
    tampon = io.BytesIO()
    image.save(tampon, "WEBP", quality=QUALITE_WEBP, method=6)
    return ContentFile(tampon.getvalue(), name=f"{nom}.webp")


# --- Illustrations générées -------------------------------------------------------------

def _couleur(teinte, saturation, luminosite):
    r, g, b = colorsys.hls_to_rgb(teinte, luminosite, saturation)
    return int(r * 255), int(g * 255), int(b * 255)


def _teinte(texte):
    """Teinte stable par molécule : tous les produits d'une même DCI partagent une couleur."""
    return int(hashlib.md5(texte.lower().encode()).hexdigest()[:4], 16) / 0xFFFF


def _police(taille, gras=False):
    return ImageFont.truetype(POLICE_GRAS if gras else POLICE, taille)


def _texte_ajuste(dessin, texte, largeur_max, taille_max, gras=False, taille_min=14):
    taille = taille_max
    while taille > taille_min:
        police = _police(taille, gras)
        if dessin.textlength(texte, font=police) <= largeur_max:
            return police
        taille -= 2
    return _police(taille_min, gras)


def _lignes_nom(dessin, nom, largeur_max):
    """Découpe le nom sur une ou deux lignes, avec la plus grande police qui tient."""
    for taille in range(46, 28, -2):
        if dessin.textlength(nom, font=_police(taille, True)) <= largeur_max:
            return [nom], _police(taille, True)
    mots = nom.split()
    if len(mots) > 1:
        coupures = [(" ".join(mots[:i]), " ".join(mots[i:])) for i in range(1, len(mots))]
        for taille in range(36, 18, -2):
            police = _police(taille, True)
            for ligne1, ligne2 in coupures:
                if max(dessin.textlength(ligne1, font=police), dessin.textlength(ligne2, font=police)) <= largeur_max:
                    return [ligne1, ligne2], police
    return [nom], _texte_ajuste(dessin, nom, largeur_max, 28, gras=True)


def _centre(dessin, texte, cx, y, police, couleur):
    largeur = dessin.textlength(texte, font=police)
    dessin.text((cx - largeur / 2, y), texte, font=police, fill=couleur)


def _icone_forme(dessin, forme, principale, claire):
    """Petit objet à côté de la boîte, selon la forme galénique."""
    blanc, contour, gris = (255, 255, 255), (148, 163, 184), (226, 232, 240)
    if forme == "comprime":
        dessin.rounded_rectangle((452, 438, 600, 548), radius=14, fill=gris, outline=contour, width=3)
        for i in range(3):
            for j in range(2):
                x, y = 478 + i * 48, 466 + j * 52
                dessin.ellipse((x - 17, y - 17, x + 17, y + 17), fill=blanc, outline=contour, width=2)
    elif forme == "gelule":
        dessin.rounded_rectangle((456, 470, 604, 524), radius=27, fill=blanc, outline=contour, width=3)
        dessin.rounded_rectangle((456, 470, 530, 524), radius=27, fill=principale)
        dessin.rectangle((503, 470, 530, 524), fill=principale)
    elif forme in ("sirop", "suspension"):
        dessin.rounded_rectangle((498, 382, 546, 408), radius=6, fill=principale)
        dessin.rectangle((506, 404, 538, 426), fill=(180, 120, 60))
        dessin.rounded_rectangle((470, 422, 574, 560), radius=22, fill=(205, 140, 70))
        dessin.rounded_rectangle((482, 462, 562, 520), radius=8, fill=blanc)
        dessin.rectangle((490, 482, 554, 492), fill=principale)
    elif forme == "injectable":
        dessin.rounded_rectangle((500, 410, 552, 432), radius=5, fill=principale)
        dessin.rectangle((510, 430, 542, 446), fill=contour)
        dessin.rounded_rectangle((490, 444, 562, 560), radius=14, fill=(224, 242, 254), outline=contour, width=3)
        dessin.rectangle((498, 490, 554, 520), fill=blanc)
    elif forme == "pommade":
        dessin.polygon([(452, 470), (580, 452), (580, 548), (452, 530)], fill=blanc, outline=contour)
        dessin.rounded_rectangle((578, 476, 612, 524), radius=6, fill=principale)
        dessin.rectangle((470, 484, 560, 516), fill=claire)
    elif forme == "sachet":
        dessin.rectangle((462, 432, 594, 556), fill=blanc, outline=contour, width=3)
        dents = [(462 + k * 11, 432 - (6 if k % 2 else 0)) for k in range(13)]
        dessin.line(dents, fill=contour, width=3)
        dessin.rectangle((478, 476, 578, 512), fill=claire)
    else:
        dessin.ellipse((470, 430, 590, 550), fill=blanc, outline=contour, width=3)
        dessin.rectangle((518, 450, 542, 530), fill=principale)
        dessin.rectangle((490, 478, 570, 502), fill=principale)


def generer_illustration(medicament):
    """Illustration de boîte (WebP) pour un médicament, sans aucune ressource externe."""
    teinte = _teinte(medicament.dci or medicament.nom_commercial)
    fond = _couleur(teinte, 0.35, 0.95)
    halo = _couleur(teinte, 0.40, 0.89)
    principale = _couleur(teinte, 0.55, 0.40)
    claire = _couleur(teinte, 0.50, 0.84)
    flanc = _couleur(teinte, 0.45, 0.70)

    image = Image.new("RGB", (COTE, COTE), fond)
    dessin = ImageDraw.Draw(image)
    dessin.ellipse((70, 50, 570, 550), fill=halo)

    # Ombre portée floue
    ombre = Image.new("L", (COTE, COTE), 0)
    ImageDraw.Draw(ombre).ellipse((110, 470, 560, 530), fill=110)
    ombre = ombre.filter(ImageFilter.GaussianBlur(18))
    image.paste((15, 23, 42), mask=ombre)
    dessin = ImageDraw.Draw(image)

    # Boîte en perspective : dessus, flanc, face
    gauche, haut, droite, bas, prof = 110, 190, 430, 480, 56
    dessin.polygon([(gauche, haut), (gauche + prof, haut - prof), (droite + prof, haut - prof), (droite, haut)], fill=claire)
    dessin.polygon([(droite, haut), (droite + prof, haut - prof), (droite + prof, bas - prof), (droite, bas)], fill=flanc)
    dessin.rectangle((gauche, haut, droite, bas), fill=(255, 255, 255))
    dessin.rectangle((gauche, haut, droite, haut + 56), fill=principale)
    dessin.rectangle((gauche, bas - 18, droite, bas), fill=principale)

    cx, largeur_utile = (gauche + droite) / 2, droite - gauche - 36
    blanc, encre, gris = (255, 255, 255), (15, 23, 42), (100, 116, 139)

    # Bandeau : mention claire qu'il s'agit d'une illustration, et « Rx » si ordonnance.
    dessin.text((gauche + 18, haut + 16), "ILLUSTRATION", font=_police(20, gras=True), fill=blanc)
    if medicament.ordonnance_requise:
        dessin.rounded_rectangle((droite - 64, haut + 11, droite - 14, haut + 45), radius=10, fill=(220, 38, 38))
        _centre(dessin, "Rx", droite - 39, haut + 15, _police(20, gras=True), blanc)

    # Nom commercial : une ligne si possible, sinon deux.
    lignes, police_nom = _lignes_nom(dessin, medicament.nom_commercial, largeur_utile)
    y = haut + 78
    for ligne in lignes:
        _centre(dessin, ligne, cx, y, police_nom, encre)
        y += police_nom.size + 6
    y += 8
    if medicament.dosage:
        police_dosage = _texte_ajuste(dessin, medicament.dosage, largeur_utile, 34, gras=True)
        _centre(dessin, medicament.dosage, cx, y, police_dosage, principale)
        y += police_dosage.size + 12
    _centre(dessin, medicament.get_forme_display(), cx, y, _police(22), gris)
    y += 22 + 10
    place_pour_dci = y <= bas - 48
    if place_pour_dci and medicament.dci and medicament.dci.lower() != medicament.nom_commercial.lower():
        police_dci = _texte_ajuste(dessin, medicament.dci, largeur_utile, 18)
        _centre(dessin, medicament.dci, cx, bas - 48, police_dci, gris)

    _icone_forme(dessin, medicament.forme, principale, claire)
    _centre(dessin, "Illustration — photo non contractuelle", COTE / 2, COTE - 42, _police(17), (100, 116, 139))

    tampon = io.BytesIO()
    image.save(tampon, "WEBP", quality=85, method=6)
    return ContentFile(tampon.getvalue(), name=f"{nom_fichier(medicament)}.webp")
