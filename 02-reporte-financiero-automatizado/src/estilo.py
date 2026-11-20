"""Estilo visual compartido por los gráficos del portafolio.

Paleta categórica validada para daltonismo + tokens de texto y superficie.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
GRAY = "#b8b6ad"
SURF, CARD = "#f4f3ef", "#fcfcfb"
TXT, TXT2, MUTED, GRID = "#0b0b0b", "#52514e", "#7b7a74", "#e4e2db"
BLUES = ["#eaf2fc", "#c4dbf6", "#93bcee", "#5c97e2", "#2a78d6", "#1d5aa6", "#123d73"]
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"],
    "font.size": 11,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TXT2,
    "xtick.color": TXT2,
    "ytick.color": TXT2,
    "axes.titlecolor": TXT,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.titlepad": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "figure.facecolor": SURF,
    "axes.facecolor": CARD,
})


def money(x, _=None):
    """Formatea montos: 1.2 M, 35 k, 820."""
    if abs(x) >= 1_000_000:
        return f"${x / 1_000_000:.1f} M"
    if abs(x) >= 1_000:
        return f"${x / 1_000:.0f} k"
    return f"${x:.0f}"


def header(fig, title, subtitle):
    fig.text(0.035, 0.955, title, fontsize=24, fontweight="bold", color=TXT)
    fig.text(0.035, 0.918, subtitle, fontsize=12.5, color=TXT2)
    fig.text(0.965, 0.955, "Oscar Arnez | Analista de Datos", fontsize=11, color=MUTED, ha="right")
    fig.text(0.965, 0.928, "Proyecto de portafolio - datos simulados", fontsize=10, color=MUTED, ha="right")


def kpi(fig, x, y, w, h, label, value, nota=None):
    ax = fig.add_axes([x, y, w, h])
    ax.set_facecolor(CARD)
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.text(0.07, 0.72, label, fontsize=11.5, color=TXT2, transform=ax.transAxes)
    ax.text(0.07, 0.30, value, fontsize=24, fontweight="bold", color=TXT, transform=ax.transAxes)
    if nota:
        ax.text(0.93, 0.36, nota, fontsize=10.5, color=TXT2, ha="right", transform=ax.transAxes)


def kpi_row(fig, items, y=0.76, h=0.12):
    """Fila de 4 indicadores. items = [(label, value, nota|None), ...]."""
    kw, gap = 0.215, 0.0133
    for i, it in enumerate(items):
        kpi(fig, 0.035 + i * (kw + gap), y, kw, h, *it)


def panel_texto(ax, titulo, texto, size=11.5):
    ax.set_facecolor(CARD)
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(titulo)
    ax.text(0.03, 0.88, texto, va="top", fontsize=size, color=TXT, linespacing=1.35, transform=ax.transAxes)


def hbar_labels(ax, valores, fmt):
    for i, v in enumerate(valores):
        ax.text(v, i, "  " + fmt(v), va="center", fontsize=10.5, color=TXT)
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
