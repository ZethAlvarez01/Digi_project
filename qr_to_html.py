"""qr_to_html.py — QR 3D con huevo emergente animado.

Todos los 441 módulos (21×21) se renderizan como cubos CSS 3D.
Al presionar el botón los cubos dentro del footprint 12×12 del huevo
suben a su altura target (definida en huevo.txt) con stagger center-first.

El CSS Houdini @property --h hace que la custom property sea animable
con transition, así todas las caras del cubo se ajustan al mismo tiempo.
"""

import webbrowser
from pathlib import Path

import qrcode

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
                        egg: list[list[tuple[int, int]]]) -> str:
    """Renderiza los 441 módulos QR con data-target, data-bot y stagger."""
    parts: list[str] = []
    max_top_px = (_EGG_MAX_TOP + EGG_LIFT) * CUBE_H   # 390 px

    for r in range(n):
        for c in range(n):
            active      = matrix[r][c]
            cls         = "active" if active else "inactive"
            x           = c * CUBE_S
            y           = r * CUBE_S
            col_h_px, bot_px = get_egg_targets(r, c, egg)
            top_px      = col_h_px + bot_px

            up_delay   = round((1 - top_px / max_top_px) * 420)
            down_delay = round((top_px / max_top_px) * 420)

            parts.append(
                f'<div class="module {cls}" '
                f'style="left:{x}px;top:{y}px;" '
                f'data-target="{col_h_px}" '
                f'data-bot="{bot_px}" '
                f'data-up-delay="{up_delay}" '
                f'data-down-delay="{down_delay}">'
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
  inherits: true;
  initial-value: {base_h}px;
}}
@property --bot {{
  syntax: "<length>";
  inherits: true;
  initial-value: 0px;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  background: #080010;
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
    0 0 6px 3px {glow1},
    0 0 18px 8px {glow2},
    inset 0 0 6px 3px {glow1};
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
  transition: --h .55s cubic-bezier(.34,1.56,.64,1),
              --bot .55s cubic-bezier(.34,1.56,.64,1);
  transform: translateZ(var(--bot));
}}

/* ---- Caras base ---- */
.face {{
  position: absolute;
  transform-style: preserve-3d;
}}

/* TOP — siempre sube a var(--h) */
.face.top {{
  width: {cube_s}px;
  height: {cube_s}px;
  top: 0; left: 0;
  transform: translateZ(var(--h));
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
</style>
</head>
<body>

<div class="scene">
  <div class="board-wrapper" id="wrapper">
    <div class="board-frame">
      <div class="board" id="board">
{modules_html}
      </div>
    </div>
  </div>
</div>

<button class="btn-egg" id="btn">🥚 Reveal Egg</button>

<script>
/* ---- Partículas ---- */
(function() {{
  for (let i = 0; i < 28; i++) {{
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

/* ---- Egg reveal ---- */
(function() {{
  const btn     = document.getElementById("btn");
  const modules = document.querySelectorAll(".module");
  const BASE    = {base_h};
  let eggVisible = false;

  function setHeights(toEgg) {{
    modules.forEach(m => {{
      const delay  = toEgg ? m.dataset.upDelay : m.dataset.downDelay;
      const newH   = toEgg ? parseInt(m.dataset.target) : BASE;
      const newBot = toEgg ? parseInt(m.dataset.bot)    : 0;
      m.style.transitionDelay = delay + "ms";
      m.style.setProperty("--h",   newH   + "px");
      m.style.setProperty("--bot", newBot + "px");
    }});
  }}

  btn.addEventListener("click", () => {{
    eggVisible = !eggVisible;
    setHeights(eggVisible);
    btn.textContent = eggVisible ? "🔄 Reset QR" : "🥚 Reveal Egg";
    btn.style.boxShadow = eggVisible
      ? "0 0 22px 8px {glow1}"
      : "0 0 12px 4px {glow2}";
  }});
}})();
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

    egg       = compute_egg_heights()
    modules   = build_modules_html(matrix, n, egg)
    board_px  = n * CUBE_S

    html = HTML_TEMPLATE.format(
        modules_html=modules,
        board_px=board_px,
        cube_s=CUBE_S,
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
