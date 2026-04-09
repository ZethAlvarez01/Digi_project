"""qr_to_html.py — QR 3D con huevo emergente animado.

Todos los 441 módulos (21×21) se renderizan como cubos CSS 3D.
Al presionar el botón los cubos dentro del footprint 12×12 del huevo
suben a su altura target (definida en huevo.txt) con stagger center-first.

El CSS Houdini @property --h hace que la custom property sea animable
con transition, así todas las caras del cubo se ajustan al mismo tiempo.
"""

import re
import webbrowser
import zipfile
from pathlib import Path

import qrcode

# ---------------------------------------------------------------------------
# Colores Digi-Egg desde huevo_color.xlsx
# ---------------------------------------------------------------------------
# Paleta confirmada del xlsx:
#   style 1 ("." transparente) → blanco (esquinas)
#   style 2 ("W" cuerpo)       → #FFFFFF
#   style 3 ("G" motitas)      → #92D050
#   style 4 ("N" espiral)      → #1a1a3a

# Colores de cara lateral  (del dump Excel: fill[2]=92D050=VERDE, fill[3]=theme=BLANCO)
# style 1,4 → no-fill / borde (fuera del huevo)
# style 2,5 → #92D050 verde  (fill solid)
# style 3,6 → #ffffff blanco (fill theme)
_DIGI_COLOR: dict[int, str] = {
    1: "#f0f0f0",   # fuera del huevo
    2: "#92d050",   # VERDE  ← fill[2] = FF92D050
    3: "#ffffff",   # BLANCO ← fill[3] = theme"2"
    4: "#f0f0f0",   # fuera (variante frame2)
    5: "#92d050",   # VERDE  (bold, frame2)
    6: "#ffffff",   # BLANCO (bold, frame2)
}

# Cara superior: tono ligeramente más oscuro para dar profundidad
_DIGI_TOP_MOD: dict[int, str] = {
    1: "#e0e0e0",
    2: "#7ab840",   # verde oscuro (top del cubo verde)
    3: "#f0fff0",   # blanco con leve tinte verde (top del cubo blanco)
    4: "#e0e0e0",
    5: "#7ab840",
    6: "#f0fff0",
}


def make_lateral_stops(col_h: int, bot: int,
                        grid: list[list[int]], ec: int) -> str:
    """Genera string de colores pipe-separados para la cara lateral.

    El mapping Z ↔ er es:
        CSS top de la cara  (y=0, Z más bajo)  → er = 11 - bot
        CSS y = i*CUBE_H                         → er = 11 - bot - i
        CSS bottom          (Z más alto)        → er = 12 - bot - col_h

    CSS top aparece más abajo en pantalla (isométrico 60°),
    CSS bottom aparece más arriba → gradiente de bottom de huevo a top.
    """
    stops: list[str] = []
    for i in range(col_h):
        er = 11 - bot - i
        if 0 <= er < EGG_N:
            color = _DIGI_COLOR.get(grid[er][ec], "#f0f0f0")
        else:
            color = "#f0f0f0"
        stops.append(color)
    return "|".join(stops)


def load_digi_grid(path: str = "huevo_color.xlsx") -> tuple[list[list[int]], list[list[int]]] | None:
    """Lee el xlsx y devuelve (grid_f1, grid_f2): dos matrices 12×12 de style-index.
    hoja1=frame1 (laterales F1), hoja2=frame2 (laterales F2).
    Retorna None si el archivo no existe.
    """
    p = Path(path)
    if not p.exists():
        return None
    with zipfile.ZipFile(p) as z:
        sheets = sorted(s for s in z.namelist()
                        if s.startswith("xl/worksheets/sheet"))
        if len(sheets) < 1:
            return None

        def parse(sheet_xml: str) -> list[list[int]]:
            cell_styles: dict[tuple[str, int], int] = {}
            for m in re.finditer(r'<c r="([A-Z]+)(\d+)"[^>]*s="(\d+)"', sheet_xml):
                cell_styles[(m.group(1), int(m.group(2)))] = int(m.group(3))
            COLS = list("FGHIJKLMNOPQ")
            return [
                [cell_styles.get((col, row), 1) for col in COLS]
                for row in range(5, 17)
            ]

        grid_f1 = parse(z.read(sheets[0]).decode("utf-8"))
        grid_f2 = parse(z.read(sheets[1]).decode("utf-8")) if len(sheets) > 1 else grid_f1

    return grid_f1, grid_f2

# ---------------------------------------------------------------------------
# Constantes visuales
# ---------------------------------------------------------------------------
CUBE_S    = 22    # px — ancho/alto de cada módulo en XY
CUBE_H    = 26    # px — altura de 1 capa (unidad de altura del huevo)
BASE_H    = CUBE_H  # altura base: 1 capa (QR plano)

# Offset para centrar el huevo 12×12 dentro del QR 21×21
# (21 - 12) // 2 = 4  → el huevo ocupa cols/rows 4..15
EGG_N     = 12
EGG_OFF   = (21 - EGG_N) // 2   # = 4  → egg ocupa rows/cols 4..15

GLOW1 = "#b400ff"
GLOW2 = "#7700aa"

# Caras — módulo ACTIVO (oscuro)
A_TOP   = "#0a0019"
A_FRONT = "#3d0080"
A_RIGHT = "#300068"
A_LEFT  = "#280058"
A_BACK  = "#200048"

# Caras — módulo INACTIVO (claro)
I_TOP   = "#f0eaff"
I_FRONT = "#c8b8ee"
I_RIGHT = "#b8a8de"
I_LEFT  = "#b0a0d8"
I_BACK  = "#a898cc"


# ---------------------------------------------------------------------------
# Heightmap del huevo  (huevo.txt, de abajo nl-12 → arriba nl-1)
# ---------------------------------------------------------------------------
# Huevo según Excel: cada nivel es 1 cubo de alto, apilados de abajo (nl-12)
# hacia arriba (nl-1). Para cada celda XY se calcula:
#   bot  = cuántos cubos desde el piso hasta donde empieza la columna
#   col_h = cuántos cubos de alto tiene la columna
#   top  = bot + col_h = altura absoluta de la cima
#
#   d=0  12×12 ring, niveles 6-9  → bot=3, col_h=4,  top=7
#   d=1  10×10 ring, niveles 4-10 → bot=2, col_h=7,  top=9
#   d=2   8×8 ring, niveles 3-11  → bot=1, col_h=9,  top=10
#   d=3   6×6 ring, niveles 2-12  → bot=0, col_h=11, top=11
#   d≥4   4×4 centro, niveles 1-12→ bot=0, col_h=12, top=12

# (col_h, bot) en cubos por distancia al borde del grid 12×12
_EGG_BY_D: dict[int, tuple[int, int]] = {
    0: (4,  3),
    1: (7,  2),
    2: (9,  1),
    3: (11, 0),
}
_EGG_DEFAULT   = (12, 0)   # d≥4
_EGG_MAX_TOP   = 12        # top absoluto máximo en cubos (sin lift)
EGG_LIFT       = 3         # cubos extra que eleva todo el huevo sobre el QR

# Cubos que se eliminan del TOP por distancia en Frame 2 (contracción)
_EGG_F2_RED: dict[int, int] = {
    1: 1,   # nivel 4 desaparece del top de d=1
    2: 1,   # nivel 3
    3: 2,   # niveles 2 y 3
    4: 2,   # niveles 1 y 2  ← fix: nivel 11 no existe en Frame 2
    5: 2,   # mismo
}

# Niveles que EXPANDEN en Frame 2 (nivel, f1_size, f2_size, z_desde_abajo)
# nivel 12 = z=0 (base), nivel 1 = z=11 (cima)
EXPANDING_LEVELS: list[tuple[int, int, int, int]] = [
    (12, 6,  10, 0),
    (11, 8,  12, 1),
    (10, 10, 14, 2),
    (9,  12, 14, 3),
    (8,  12, 14, 4),
]


def get_ring_delta(f1: int, f2: int) -> list[tuple[int, int]]:
    """Celdas en egg-coords que están en f2 pero NO en f1 (centrado en 12×12)."""
    f1_off = (EGG_N - f1) // 2          # puede ser negativo si f2>EGG_N
    f2_off = (EGG_N - f2) // 2
    f1_cells = {
        (r, c)
        for r in range(f1_off, f1_off + f1)
        for c in range(f1_off, f1_off + f1)
    }
    return [
        (r, c)
        for r in range(f2_off, f2_off + f2)
        for c in range(f2_off, f2_off + f2)
        if (r, c) not in f1_cells
    ]


def egg_to_board_px(er: int, ec: int) -> tuple[int, int]:
    """Convierte coords egg (pueden ser negativas) a px en el board."""
    return (ec + EGG_OFF) * CUBE_S, (er + EGG_OFF) * CUBE_S  # x, y


def _ring_dist(er: int, ec: int, f1: int) -> int:
    """Distancia Chebyshev de la celda al borde exterior del cuadrado f1.
    Celdas adyacentes al f1 = 1, una más afuera = 2, etc."""
    lo = (EGG_N - f1) // 2
    hi = lo + f1 - 1
    dr = max(0, lo - er, er - hi)
    dc = max(0, lo - ec, ec - hi)
    return max(dr, dc)


def build_pulse_rings_html(matrix: list[list[bool]], n: int,
                           digi: tuple[list[list[int]], list[list[int]]] | None = None) -> str:
    """Genera divs de anillo de expansión. Invisibles hasta reveal."""
    parts: list[str] = []
    grid_f1 = digi[0] if digi else None
    grid_f2 = digi[1] if digi else None

    for _nivel, f1, f2, z_idx in EXPANDING_LEVELS:
        bot_px    = (z_idx + EGG_LIFT) * CUBE_H
        delta     = get_ring_delta(f1, f2)
        delta_set = set(delta)

        # Z-mapping: la fila del patrón que corresponde a este nivel Z
        # er_pattern = 11 - z_level_sin_lift  (mismo que make_lateral_stops usa)
        er_pattern = 11 - z_idx

        for er, ec in delta:
            x, y = egg_to_board_px(er, ec)
            br, bc = er + EGG_OFF, ec + EGG_OFF
            qr_cls = "qr-active" if (0 <= br < n and 0 <= bc < n
                                     and matrix[br][bc]) else "qr-inactive"

            # Color del ring: fila del patrón = er_pattern (Z-mapped), columna = ec
            # ec puede salir del grid (rings que expanden más allá de 12×12)
            if grid_f1 and 0 <= er_pattern < EGG_N and 0 <= ec < EGG_N:
                sf1 = grid_f1[er_pattern][ec]
                sf2 = grid_f2[er_pattern][ec] if grid_f2 else sf1
            else:
                sf1 = sf2 = 3  # blanco por defecto (fuera de rango del patrón)
            digi_side_f1 = _DIGI_COLOR.get(sf1, "#f0f0f0")
            digi_side_f2 = _DIGI_COLOR.get(sf2, "#f0f0f0")

            dist     = _ring_dist(er, ec, f1)
            delay_ms = z_idx * 60 + (dist - 1) * 30

            faces = '<div class="face top"></div><div class="face bottom"></div>'
            if (er - 1, ec) not in delta_set:
                faces += '<div class="face back"></div>'
            if (er + 1, ec) not in delta_set:
                faces += '<div class="face front"></div>'
            if (er, ec - 1) not in delta_set:
                faces += '<div class="face left"></div>'
            if (er, ec + 1) not in delta_set:
                faces += '<div class="face right"></div>'

            parts.append(
                f'<div class="pulse-ring {qr_cls}" '
                f'style="left:{x}px;top:{y}px;transform:translateZ({bot_px}px);" '
                f'data-ring-delay="{delay_ms}" '
                f'data-digi-side-f1="{digi_side_f1}" '
                f'data-digi-side-f2="{digi_side_f2}">'
                f'{faces}</div>'
            )
    return "\n".join(parts)


def compute_egg_heights() -> list[list[tuple[int, int]]]:
    """Devuelve matrix 12×12 con (col_h, bot) en cubos para cada celda."""
    grid = []
    for r in range(EGG_N):
        row = []
        for c in range(EGG_N):
            d = min(r, EGG_N - 1 - r, c, EGG_N - 1 - c)
            row.append(_EGG_BY_D.get(d, _EGG_DEFAULT))
        grid.append(row)
    return grid


def get_egg_targets(qr_r: int, qr_c: int,
                    egg: list[list[tuple[int, int]]]) -> tuple[int, int]:
    """Devuelve (col_h_px, bot_px). Fuera del huevo → (BASE_H, 0)."""
    er = qr_r - EGG_OFF
    ec = qr_c - EGG_OFF
    if 0 <= er < EGG_N and 0 <= ec < EGG_N:
        col_h, bot = egg[er][ec]
        return col_h * CUBE_H, (bot + EGG_LIFT) * CUBE_H
    return BASE_H, 0


# ---------------------------------------------------------------------------
# Generación de HTML de módulos
# ---------------------------------------------------------------------------

def build_modules_html(matrix: list[list[bool]], n: int,
                        egg: list[list[tuple[int, int]]],
                        digi: tuple[list[list[int]], list[list[int]]] | None = None) -> str:
    """Renderiza los 441 módulos QR con data-target, data-bot y stagger."""
    parts: list[str] = []
    max_top_px = (_EGG_MAX_TOP + EGG_LIFT) * CUBE_H

    grid_f1 = digi[0] if digi else None
    grid_f2 = digi[1] if digi else None

    for r in range(n):
        for c in range(n):
            active = matrix[r][c]
            cls    = "active" if active else "inactive"
            x           = c * CUBE_S
            y           = r * CUBE_S
            col_h_px, bot_px = get_egg_targets(r, c, egg)
            top_px           = col_h_px + bot_px

            # Frame 2: contracción vertical (top se hunde según d-ring)
            er, ec = r - EGG_OFF, c - EGG_OFF
            if 0 <= er < EGG_N and 0 <= ec < EGG_N:
                d      = min(er, EGG_N - 1 - er, ec, EGG_N - 1 - ec)
                red    = _EGG_F2_RED.get(d, 0)
                f2h_px = col_h_px - red * CUBE_H
            else:
                f2h_px = col_h_px

            up_delay   = round((1 - top_px / max_top_px) * 420)
            down_delay = round((top_px / max_top_px) * 420)

            # Colores Digi-Egg (gradientes por nivel Z, solo celdas del egg)
            digi_attrs = ""
            if grid_f1 is not None and 0 <= er < EGG_N and 0 <= ec < EGG_N:
                # col_h y bot en unidades CUBE_H, sin el lift
                col_h_u = col_h_px // CUBE_H
                bot_u   = (bot_px - EGG_LIFT * CUBE_H) // CUBE_H
                f2h_u   = f2h_px  // CUBE_H

                # Top face: Z-mapped al er del patrón que queda en la cima de esta columna
                # er_top = 12 - bot_u - col_h  (el i=col_h-1 de make_lateral_stops)
                er_top_f1 = 12 - bot_u - col_h_u
                er_top_f2 = 12 - bot_u - f2h_u
                sf1_top   = grid_f1[er_top_f1][ec] if 0 <= er_top_f1 < EGG_N else 1
                sf2_top   = (grid_f2 or grid_f1)[er_top_f2][ec] if 0 <= er_top_f2 < EGG_N else 1
                digi_top_f1 = _DIGI_TOP_MOD.get(sf1_top, "#e0e0e0")
                digi_top_f2 = _DIGI_TOP_MOD.get(sf2_top, "#e0e0e0")

                stops_f1 = make_lateral_stops(col_h_u, bot_u, grid_f1, ec)
                stops_f2 = make_lateral_stops(f2h_u,   bot_u, grid_f2 or grid_f1, ec)
                digi_attrs = (
                    f'data-digi-top="{digi_top_f1}" '
                    f'data-digi-top-f2="{digi_top_f2}" '
                    f'data-digi-stops-f1="{stops_f1}" '
                    f'data-digi-stops-f2="{stops_f2}" '
                )

            parts.append(
                f'<div class="module {cls}" '
                f'style="left:{x}px;top:{y}px;--hf2:{f2h_px}px;" '
                f'data-target="{col_h_px}" '
                f'data-bot="{bot_px}" '
                f'data-up-delay="{up_delay}" '
                f'data-down-delay="{down_delay}" '
                f'{digi_attrs}>'
                '<div class="face top"></div>'
                '<div class="face front"></div>'
                '<div class="face right"></div>'
                '<div class="face left"></div>'
                '<div class="face back"></div>'
                '</div>'
            )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Template HTML
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QR 3D — Hola Zeth!</title>
<style>
@property --h {{
  syntax: "<length>";
  inherits: false;
  initial-value: {base_h}px;
}}
@property --bot {{
  syntax: "<length>";
  inherits: false;
  initial-value: 0px;
}}
@property --hf2 {{
  syntax: "<length>";
  inherits: false;
  initial-value: {base_h}px;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  background: #1a3a20;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  user-select: none;
  font-family: sans-serif;
}}

/* ---- Partículas ---- */
.particle {{
  position: fixed;
  border-radius: 50%;
  background: {glow1};
  opacity: 0;
  pointer-events: none;
  animation: drift linear infinite;
}}
@keyframes drift {{
  0%   {{ transform: translateY(100vh); opacity: 0; }}
  10%  {{ opacity: .4; }}
  90%  {{ opacity: .4; }}
  100% {{ transform: translateY(-10vh); opacity: 0; }}
}}

/* ---- Botón ---- */
.btn-egg {{
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  padding: 12px 32px;
  background: #0053e2;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: .06em;
  cursor: pointer;
  box-shadow: 0 0 12px 4px {glow2};
  transition: background .15s, box-shadow .15s, transform .1s;
}}
.btn-egg:hover  {{ background: #1a63f0; box-shadow: 0 0 18px 6px {glow1}; }}
.btn-egg:active {{ transform: translateX(-50%) scale(.96); }}

/* ---- Escena 3D ---- */
.scene {{
  perspective: 1100px;
  perspective-origin: 50% -10%;
  transform-style: preserve-3d;
  display: flex;
  align-items: center;
  justify-content: center;
}}

.board-wrapper {{
  transform-style: preserve-3d;
  transform: rotateX(60deg) rotateZ(-15deg);
  animation: float 7s ease-in-out infinite;
  cursor: grab;
  will-change: transform;
}}
.board-wrapper.dragging {{ cursor: grabbing; }}

@keyframes float {{
  0%,100% {{ transform: rotateX(60deg) rotateZ(-15deg) translateY(0); }}
  50%      {{ transform: rotateX(60deg) rotateZ(-15deg) translateY(-14px); }}
}}

/* ---- Marco exterior ---- */
.board-frame {{
  padding: {cube_s}px;
  background: #fff;
  border: {cube_s}px solid #000;
  box-shadow:
    0 0 10px 4px {glow1},
    0 0 28px 10px {glow2};
  transform-style: preserve-3d;
  overflow: visible;
}}

/* ---- Board ---- */
.board {{
  position: relative;
  width: {board_px}px;
  height: {board_px}px;
  transform-style: preserve-3d;
  overflow: visible;
}}

/* ---- Módulo ---- */
.module {{
  position: absolute;
  width: {cube_s}px;
  height: {cube_s}px;
  transform-style: preserve-3d;
  overflow: visible;
  /* Sin transition aquí: reveal/hide la activan por inline style;
     setFrame hace snap puro (no hay CSS que pelee) */
  transform: translateZ(var(--bot));
}}

/* Frame2: --hf2 bakeado inline en cada módulo; !important gana sobre inline --h */
.board.frame2 .module {{
  --h: var(--hf2) !important;
}}
/* Switching: bloquea cualquier transición activa durante el snap */
.board.switching .module,
.board.switching .module .face {{
  transition: none !important;
}}

/* ---- Caras base ---- */
.face {{
  position: absolute;
  transform-style: preserve-3d;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}}

/* TOP — siempre sube a var(--h) */
.face.top {{
  width: {cube_s}px;
  height: {cube_s}px;
  top: 0; left: 0;
  transform: translateZ(var(--h));
  /* sin transition: snap instantáneo en setFrame */
}}

/* Caras laterales */

/* Digi-Egg colorized — clase .digi añadida por JS tras el reveal */
/* F1 (default) */
.module.digi .face.top   {{ background: var(--digi-top,   #f0fff0) !important; }}
.module.digi .face.front {{ background: var(--digi-front, #f0f0f0) !important; }}
.module.digi .face.right {{ background: var(--digi-right, #f0f0f0) !important; }}
.module.digi .face.left  {{ background: var(--digi-left,  #f0f0f0) !important; }}
.module.digi .face.back  {{ background: var(--digi-back,  #f0f0f0) !important; }}
/* F2 — sobrescribe via clase en el board */
.board.frame2 .module.digi .face.top   {{ background: var(--digi2-top,   #f0fff0) !important; }}
.board.frame2 .module.digi .face.front {{ background: var(--digi2-front, #f0f0f0) !important; }}
.board.frame2 .module.digi .face.right {{ background: var(--digi2-right, #f0f0f0) !important; }}
.board.frame2 .module.digi .face.left  {{ background: var(--digi2-left,  #f0f0f0) !important; }}
.board.frame2 .module.digi .face.back  {{ background: var(--digi2-back,  #f0f0f0) !important; }}

/* Rings: F1 default */
.pulse-ring.digi .face.top    {{ background: var(--digi-front, #f0f0f0) !important; }}
.pulse-ring.digi .face.bottom {{ background: var(--digi-front, #f0f0f0) !important; }}
.pulse-ring.digi .face.front  {{ background: var(--digi-front, #f0f0f0) !important; }}
.pulse-ring.digi .face.right  {{ background: var(--digi-right, #f0f0f0) !important; }}
.pulse-ring.digi .face.left   {{ background: var(--digi-left,  #f0f0f0) !important; }}
.pulse-ring.digi .face.back   {{ background: var(--digi-back,  #f0f0f0) !important; }}
/* Rings F2 — via clase en el board */
.board.frame2 .pulse-ring.digi .face.top    {{ background: var(--digi2-front, #f0f0f0) !important; }}
.board.frame2 .pulse-ring.digi .face.bottom {{ background: var(--digi2-front, #f0f0f0) !important; }}
.board.frame2 .pulse-ring.digi .face.front  {{ background: var(--digi2-front, #f0f0f0) !important; }}
.board.frame2 .pulse-ring.digi .face.right  {{ background: var(--digi2-right, #f0f0f0) !important; }}
.board.frame2 .pulse-ring.digi .face.left   {{ background: var(--digi2-left,  #f0f0f0) !important; }}
.board.frame2 .pulse-ring.digi .face.back   {{ background: var(--digi2-back,  #f0f0f0) !important; }}

/* BOTTOM — cara inferior de los ring cubes */
.face.bottom {{
  width: {cube_s}px;
  height: {cube_s}px;
  top: 0; left: 0;
  transform: rotateX(180deg);  /* gira para mirar hacia -Z */
  background: #880066;
}}

/* FRONT — pivota en el borde inferior del módulo, altura = var(--h) */
.face.front {{
  width: {cube_s}px;
  height: var(--h);
  top: {cube_s}px;
  left: 0;
  transform-origin: 50% 0%;
  transform: rotateX(90deg);
}}

/* RIGHT */
.face.right {{
  width: var(--h);
  height: {cube_s}px;
  top: 0;
  left: {cube_s}px;
  transform-origin: 0% 50%;
  transform: rotateY(-90deg);
}}

/* LEFT */
.face.left {{
  width: var(--h);
  height: {cube_s}px;
  top: 0;
  left: calc(-1 * var(--h));
  transform-origin: 100% 50%;
  transform: rotateY(90deg);
}}

/* BACK */
.face.back {{
  width: {cube_s}px;
  height: var(--h);
  top: calc(-1 * var(--h));
  left: 0;
  transform-origin: 50% 100%;
  transform: rotateX(-90deg);
}}

/* ---- Colores — módulo ACTIVO ---- */
.module.active .face.top   {{ background: {a_top}; }}
.module.active .face.front {{ background: linear-gradient(to bottom, {a_front} 0%, #0a0019 100%); }}
.module.active .face.right {{ background: linear-gradient(to right,  {a_right} 0%, #0a0019 100%); }}
.module.active .face.left  {{ background: linear-gradient(to left,   {a_left}  0%, #0a0019 100%); }}
.module.active .face.back  {{ background: linear-gradient(to top,    {a_back}  0%, #0a0019 100%); }}

/* ---- Colores — módulo INACTIVO ---- */
.module.inactive .face.top   {{ background: {i_top}; }}
.module.inactive .face.front {{ background: linear-gradient(to bottom, {i_front} 0%, #d0c4f0 100%); }}
.module.inactive .face.right {{ background: linear-gradient(to right,  {i_right} 0%, #c8b8e8 100%); }}
.module.inactive .face.left  {{ background: linear-gradient(to left,   {i_left}  0%, #c0b0e0 100%); }}
.module.inactive .face.back  {{ background: linear-gradient(to top,    {i_back}  0%, #c8b8e8 100%); }}

/* ---- Anillos de expansión (pulse rings) ---- */
.pulse-ring {{
  position: absolute;
  width: {cube_s}px;
  height: {cube_s}px;
  transform-style: preserve-3d;
  overflow: visible;
}}
/* Faces invisibles al inicio; snap instantaneo — sin fade */
.pulse-ring .face {{
  opacity: 0;
}}
.pulse-ring.visible .face {{
  opacity: 1;
}}
/* — Color: módulo QR activo (hereda los colores del huevo oscuro) — */
.pulse-ring.qr-active .face.top    {{ background: {a_top}; }}
.pulse-ring.qr-active .face.bottom {{ background: {a_back}; }}
.pulse-ring.qr-active .face.front  {{ background: linear-gradient(to bottom, {a_front} 0%, {a_back} 100%); }}
.pulse-ring.qr-active .face.right  {{ background: linear-gradient(to right,  {a_right} 0%, {a_back} 100%); }}
.pulse-ring.qr-active .face.left   {{ background: linear-gradient(to left,   {a_left}  0%, {a_back} 100%); }}
.pulse-ring.qr-active .face.back   {{ background: linear-gradient(to top,    {a_front} 0%, {a_back} 100%); }}
/* — Color: módulo QR inactivo (hereda los colores del huevo claro) — */
.pulse-ring.qr-inactive .face.top    {{ background: {i_top}; }}
.pulse-ring.qr-inactive .face.bottom {{ background: {i_back}; }}
.pulse-ring.qr-inactive .face.front  {{ background: linear-gradient(to bottom, {i_front} 0%, {i_back} 100%); }}
.pulse-ring.qr-inactive .face.right  {{ background: linear-gradient(to right,  {i_right} 0%, {i_back} 100%); }}
.pulse-ring.qr-inactive .face.left   {{ background: linear-gradient(to left,   {i_left}  0%, {i_back} 100%); }}
.pulse-ring.qr-inactive .face.back   {{ background: linear-gradient(to top,    {i_front} 0%, {i_back} 100%); }}
</style>
</head>
<body>

<div class="scene">
  <div class="board-wrapper" id="wrapper">
    <div class="board-frame">
      <div class="board" id="board">
{modules_html}
{pulse_rings_html}
      </div>
    </div>
  </div>
</div>

<div style="position:fixed;bottom:32px;left:50%;transform:translateX(-50%);z-index:100;">
<button class="btn-egg" id="btn">🥚 Reveal Egg</button>
</div>

<script>
/* ---- Partículas ---- */
(function() {{
  for (let i = 0; i < 12; i++) {{
    const el = document.createElement("div");
    el.className = "particle";
    const s = 2 + Math.random();
    el.style.cssText = [
      `width:${{s.toFixed(1)}}px`, `height:${{s.toFixed(1)}}px`,
      `left:${{(Math.random()*100).toFixed(1)}}%`, `bottom:0`,
      `animation-duration:${{(4+Math.random()*8).toFixed(2)}}s`,
      `animation-delay:${{(Math.random()*8).toFixed(2)}}s`,
    ].join(";");
    document.body.appendChild(el);
  }}
}})();

/* ---- Drag libre acumulativo ---- */
(function() {{
  const wrapper = document.getElementById("wrapper");
  let rotX = 60, rotZ = -15;
  let dragging = false, lastX = 0, lastY = 0;
  let floating = true;   // true = animación CSS activa

  function killFloat() {{
    if (!floating) return;
    floating = false;
    // inline animation: none gana sobre la clase CSS → sin snap-back
    wrapper.style.animation = "none";
    wrapper.style.transform = `rotateX(${{rotX}}deg) rotateZ(${{rotZ}}deg)`;
  }}

  function apply() {{
    wrapper.style.transform = `rotateX(${{rotX}}deg) rotateZ(${{rotZ}}deg)`;
  }}

  /* Mouse */
  wrapper.addEventListener("mousedown", e => {{
    e.preventDefault();
    killFloat();   // primera interacción: mata el float para siempre (hasta dblclick)
    dragging = true;
    lastX = e.clientX; lastY = e.clientY;
    wrapper.classList.add("dragging");
  }});

  window.addEventListener("mousemove", e => {{
    if (!dragging) return;
    rotZ += (e.clientX - lastX) * 0.5;
    rotX -= (e.clientY - lastY) * 0.5;
    lastX = e.clientX; lastY = e.clientY;
    apply();
  }});

  window.addEventListener("mouseup", () => {{
    dragging = false;
    wrapper.classList.remove("dragging");
    // NO re-habilitamos la animación → el transform queda donde el usuario lo dejó
  }});

  /* Doble-click → reset completo */
  wrapper.addEventListener("dblclick", () => {{
    rotX = 60; rotZ = -15;
    floating = true;
    wrapper.style.animation = "";   // devuelve control al CSS
    wrapper.style.transform = "";
  }});

  /* Touch */
  wrapper.addEventListener("touchstart", e => {{
    killFloat();
    dragging = true;
    lastX = e.touches[0].clientX; lastY = e.touches[0].clientY;
  }}, {{passive:true}});

  wrapper.addEventListener("touchmove", e => {{
    e.preventDefault();
    if (!dragging) return;
    rotZ += (e.touches[0].clientX - lastX) * 0.5;
    rotX -= (e.touches[0].clientY - lastY) * 0.5;
    lastX = e.touches[0].clientX; lastY = e.touches[0].clientY;
    apply();
  }}, {{passive:false}});

  wrapper.addEventListener("touchend", () => {{ dragging = false; }});
}})();

/* ---- Egg reveal + Pulse 1s ---- */
(function() {{
  const btn     = document.getElementById("btn");
  const board   = document.querySelector(".board");
  const modules = board.querySelectorAll(".module");
  const rings   = board.querySelectorAll(".pulse-ring");
  const BASE    = {base_h};
  const CUBE_H_JS = {cube_h};

  let eggVisible  = false;
  let frame2      = false;
  let timer       = null;
  let colorsInited = false;

  const CASCADE = "--h .55s cubic-bezier(.34,1.56,.64,1), --bot .55s cubic-bezier(.34,1.56,.64,1)";

  /* Construye gradiente para las 4 caras laterales desde array de colores */
  function buildGrads(stops) {{
    const h   = CUBE_H_JS;
    const seg = stops.map((c, i) => `${{c}} ${{i*h}}px ${{(i+1)*h}}px`).join(",");
    return {{
      front: `linear-gradient(to bottom,${{seg}})`,
      right: `linear-gradient(to right,${{seg}})`,
      left:  `linear-gradient(to left,${{seg}})`,
      back:  `linear-gradient(to top,${{seg}})`,
    }};
  }}

  /* Bake colores F1+F2 como CSS vars en cada elemento — se llama UNA SOLA VEZ.
     setFrame ya no toca colores; el CSS toggle de .frame2 en .board lo hace. */
  function initDigiColors() {{
    if (colorsInited) return;
    colorsInited = true;
    modules.forEach(m => {{
      if (!m.dataset.digiStopsF1) return;
      const g1 = buildGrads(m.dataset.digiStopsF1.split("|"));
      const g2 = buildGrads(m.dataset.digiStopsF2.split("|"));
      m.style.setProperty("--digi-top",    m.dataset.digiTop);
      m.style.setProperty("--digi-front",  g1.front);
      m.style.setProperty("--digi-right",  g1.right);
      m.style.setProperty("--digi-left",   g1.left);
      m.style.setProperty("--digi-back",   g1.back);
      m.style.setProperty("--digi2-top",   m.dataset.digiTopF2);
      m.style.setProperty("--digi2-front", g2.front);
      m.style.setProperty("--digi2-right", g2.right);
      m.style.setProperty("--digi2-left",  g2.left);
      m.style.setProperty("--digi2-back",  g2.back);
    }});
    rings.forEach(r => {{
      if (!r.dataset.digiSideF1) return;
      const c1 = r.dataset.digiSideF1, c2 = r.dataset.digiSideF2 || c1;
      r.style.setProperty("--digi-front",  c1);
      r.style.setProperty("--digi-right",  c1);
      r.style.setProperty("--digi-left",   c1);
      r.style.setProperty("--digi-back",   c1);
      r.style.setProperty("--digi2-front", c2);
      r.style.setProperty("--digi2-right", c2);
      r.style.setProperty("--digi2-left",  c2);
      r.style.setProperty("--digi2-back",  c2);
    }});
  }}

  /* setFrame: 0 mutations en módulos — solo un toggle de clase en el board */
  function setFrame(toF2) {{
    frame2 = toF2;
    board.classList.add("switching");          // bloquea transiciones activas
    board.classList.toggle("frame2", toF2);    // CSS override de --h y colores
    rings.forEach(r => r.classList.toggle("visible", toF2));
    requestAnimationFrame(() => board.classList.remove("switching"));
  }}

  function revealEgg() {{
    initDigiColors();
    modules.forEach(m => {{
      m.style.transition      = CASCADE;
      m.style.transitionDelay = m.dataset.upDelay + "ms";
      m.style.setProperty("--h",   m.dataset.target + "px");
      m.style.setProperty("--bot", m.dataset.bot    + "px");
    }});
    /* Stagger clase .digi por fila */
    modules.forEach((m, i) => {{
      if (!m.dataset.digiStopsF1) return;
      const delay = 900 + Math.floor(i / 21) * 60;
      setTimeout(() => m.classList.add("digi"), delay);
    }});
    rings.forEach(r => r.classList.add("digi"));
  }}

  function hideEgg() {{
    /* Eliminar .frame2 antes del hide para que inline --h domine */
    board.classList.add("switching");
    board.classList.remove("frame2");
    requestAnimationFrame(() => {{
      board.classList.remove("switching");
      modules.forEach(m => {{
        m.style.transition      = CASCADE;
        m.style.transitionDelay = m.dataset.downDelay + "ms";
        m.style.setProperty("--h",   BASE + "px");
        m.style.setProperty("--bot", "0px");
        m.classList.remove("digi");
      }});
      rings.forEach(r => r.classList.remove("digi"));
    }});
  }}

  btn.addEventListener("click", () => {{
    eggVisible = !eggVisible;
    if (eggVisible) {{
      revealEgg();
      timer = setInterval(() => setFrame(!frame2), 1000);
    }} else {{
      clearInterval(timer); timer = null;
      frame2 = false;
      hideEgg();
    }}
    btn.textContent  = eggVisible ? "🔄 Reset QR" : "🥚 Reveal Egg";
    btn.style.boxShadow = eggVisible ? "0 0 22px 8px {glow1}" : "0 0 12px 4px {glow2}";
  }});
}})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Generador principal
# ---------------------------------------------------------------------------

def generate_qr_html(data: str = "Hola Zeth!", output: str = "qr_3d.html") -> Path:
    """Genera el HTML autocontenido y lo abre en el browser."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=0,
    )
    qr.add_data(data)
    qr.make(fit=False)
    matrix = qr.get_matrix()
    n = len(matrix)

    egg        = compute_egg_heights()
    digi       = load_digi_grid()
    modules    = build_modules_html(matrix, n, egg, digi)
    rings      = build_pulse_rings_html(matrix, n, digi)
    board_px   = n * CUBE_S

    html = HTML_TEMPLATE.format(
        modules_html=modules,
        pulse_rings_html=rings,
        board_px=board_px,
        cube_s=CUBE_S,
        cube_h=CUBE_H,
        base_h=BASE_H,
        glow1=GLOW1, glow2=GLOW2,
        a_top=A_TOP, a_front=A_FRONT, a_right=A_RIGHT, a_left=A_LEFT, a_back=A_BACK,
        i_top=I_TOP, i_front=I_FRONT, i_right=I_RIGHT, i_left=I_LEFT, i_back=I_BACK,
    )

    out = Path(output)
    out.write_text(html, encoding="utf-8")
    print(f"✅  HTML guardado → {out.resolve()}")
    print(f"    QR: {n}×{n} | board: {board_px}px | egg offset: {EGG_OFF} | top-max: {(_EGG_MAX_TOP+EGG_LIFT)*CUBE_H}px | lift: {EGG_LIFT} cubos")
    webbrowser.open(out.resolve().as_uri())
    return out


if __name__ == "__main__":
    generate_qr_html("Hola Zeth!")
