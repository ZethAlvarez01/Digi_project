"""qr_glow.py — QR code PNG con glow púrpura en perímetro + marco negro.

Pipeline de composición (en orden):
  1. Canvas RGB blanco
  2. shape_layer blanca → módulos en glow_color → blur ×N → multiply
  3. module_layer RGBA → módulos oscuros → paste con alpha
  4. frame_glow_layer blanca → rect outline en glow_color → blur ×N → multiply
  5. Marco negro sólido encima

Datos: "Hola Zeth!" · QR versión 1 · error correction M · 21×21 módulos
"""

from pathlib import Path

import qrcode
from PIL import Image, ImageChops, ImageDraw, ImageFilter


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


def qr_neon_glow(
    data: str,
    output: str = "qr_glow.png",
    box_size: int = 22,
    glow_color: tuple = (180, 0, 255),
    module_color: tuple = (10, 0, 25),
    bg_color: tuple = (255, 255, 255),
    glow_radius: int = 4,
    glow_layers: int = 2,
    padding: int = 30,
    border_color: tuple = (0, 0, 0),
    border_width: int = 22,
) -> Path:
    """Genera un PNG del QR con glow púrpura en el perímetro exterior de los módulos.

    El glow usa un pipeline de multiply-blending sobre capas blancas:
    · blanco × blanco = blanco  → fondo intacto
    · blanco × púrpura_borroso = púrpura → glow solo asoma fuera de los módulos
    """
    # ------------------------------------------------------------------
    # 1. Generar matriz QR 21×21
    # ------------------------------------------------------------------
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=0,
    )
    qr.add_data(data)
    qr.make(fit=False)
    matrix = qr.get_matrix()
    n = len(matrix)  # debe ser 21

    # ------------------------------------------------------------------
    # 2. Geometría
    # ------------------------------------------------------------------
    qr_size = n * box_size
    offset = padding + border_width   # píxeles desde el borde del canvas al QR
    total = qr_size + offset * 2      # canvas cuadrado total

    # ------------------------------------------------------------------
    # 3. Canvas base — fondo blanco
    # ------------------------------------------------------------------
    result = Image.new("RGB", (total, total), bg_color)

    # ------------------------------------------------------------------
    # 4. Glow de módulos (N pasadas)
    # Dibujamos todos los módulos activos como rects sólidos en glow_color
    # sobre una capa blanca, borramos y multiplicamos contra result.
    # Los vecinos comparten bordes → el blur solo "asoma" por el perímetro.
    # ------------------------------------------------------------------
    for _ in range(glow_layers):
        shape_layer = Image.new("RGB", (total, total), (255, 255, 255))
        sdraw = ImageDraw.Draw(shape_layer)
        for r, row in enumerate(matrix):
            for c, active in enumerate(row):
                if active:
                    x0 = offset + c * box_size
                    y0 = offset + r * box_size
                    sdraw.rectangle([x0, y0, x0 + box_size - 1, y0 + box_size - 1], fill=glow_color)
        shape_layer = shape_layer.filter(ImageFilter.GaussianBlur(radius=glow_radius))
        result = ImageChops.multiply(result, shape_layer)

    # ------------------------------------------------------------------
    # 5. Módulos oscuros encima (RGBA con alpha exacta → sin halo propio)
    # ------------------------------------------------------------------
    module_layer = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    mdraw = ImageDraw.Draw(module_layer)
    for r, row in enumerate(matrix):
        for c, active in enumerate(row):
            if active:
                x0 = offset + c * box_size
                y0 = offset + r * box_size
                mdraw.rectangle(
                    [x0, y0, x0 + box_size - 1, y0 + box_size - 1],
                    fill=(*module_color, 255),
                )
    result = result.convert("RGBA")
    result.paste(module_layer, (0, 0), module_layer)
    result = result.convert("RGB")

    # ------------------------------------------------------------------
    # 6. Glow del marco (N pasadas) — mismo truco multiply
    # ------------------------------------------------------------------
    for _ in range(glow_layers):
        frame_glow = Image.new("RGB", (total, total), (255, 255, 255))
        fgdraw = ImageDraw.Draw(frame_glow)
        # Outer rect: el borde exterior del trazo coincide con el canvas edge
        fgdraw.rectangle(
            [0, 0, total - 1, total - 1],
            outline=glow_color,
            width=border_width,
        )
        frame_glow = frame_glow.filter(ImageFilter.GaussianBlur(radius=glow_radius))
        result = ImageChops.multiply(result, frame_glow)

    # ------------------------------------------------------------------
    # 7. Marco negro sólido encima
    # ------------------------------------------------------------------
    fdraw = ImageDraw.Draw(result)
    fdraw.rectangle(
        [0, 0, total - 1, total - 1],
        outline=border_color,
        width=border_width,
    )

    # ------------------------------------------------------------------
    # 8. Guardar
    # ------------------------------------------------------------------
    out = Path(output)
    result.save(out, format="PNG", optimize=True)
    print(f"✅  PNG guardado → {out.resolve()}")
    print(f"    Canvas: {total}×{total}px | QR: {n}×{n} módulos | box: {box_size}px")
    return out


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    qr_neon_glow("Hola Zeth!")
