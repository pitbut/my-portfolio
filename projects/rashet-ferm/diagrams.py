# -*- coding: utf-8 -*-
"""Рисунки для фермы: расчётная схема и диаграмма усилий в стержнях."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


def _draw_support(ax, x, y, kind):
    s = 0.28
    if kind == 'pin':
        tri = patches.Polygon([[x - s * 0.6, y - s], [x + s * 0.6, y - s], [x, y]],
                               closed=True, fill=False, lw=1.6, edgecolor='k')
        ax.add_patch(tri)
        ax.plot([x - s * 0.7, x + s * 0.7], [y - s - 0.06, y - s - 0.06], color='k', lw=1.4)
        for k in range(5):
            xx = x - s * 0.6 + k * (1.2 * s / 4)
            ax.plot([xx, xx - 0.1], [y - s - 0.06, y - s - 0.18], color='k', lw=0.8)
    else:  # roller_y / roller_x
        tri = patches.Polygon([[x - s * 0.6, y - s], [x + s * 0.6, y - s], [x, y]],
                               closed=True, fill=False, lw=1.6, edgecolor='k')
        ax.add_patch(tri)
        ax.plot([x - s * 0.7, x + s * 0.7], [y - s - 0.1, y - s - 0.1], color='k', lw=1.4)


def draw_scheme(truss, loads_in, path):
    xs = [n.x for n in truss.nodes]
    ys = [n.y for n in truss.nodes]
    pad = max(1.0, 0.15 * (max(xs) - min(xs) + 1))
    fig, ax = plt.subplots(figsize=(9, 6))

    for m in truss.members:
        ni, nj = truss.nodes[m.i], truss.nodes[m.j]
        ax.plot([ni.x, nj.x], [ni.y, nj.y], color='#333', lw=2.2, zorder=2)

    for i, n in enumerate(truss.nodes):
        ax.plot(n.x, n.y, 'o', color='#222', ms=6, zorder=3)
        ax.annotate(str(i), (n.x, n.y), textcoords="offset points", xytext=(6, 6), fontsize=9)

    for s in truss.supports:
        n = truss.nodes[s.node]
        _draw_support(ax, n.x, n.y, s.kind)

    for ld in loads_in:
        n = truss.nodes[ld['node']]
        fx, fy = ld['fx'], ld['fy']
        mag = (fx ** 2 + fy ** 2) ** 0.5
        if mag < 1e-9:
            continue
        scale = 1.1 / mag
        ax.annotate('', xy=(n.x, n.y), xytext=(n.x - fx * scale, n.y - fy * scale),
                    arrowprops=dict(arrowstyle='-|>', color='tab:red', lw=2), zorder=4)
        ax.text(n.x - fx * scale, n.y - fy * scale, f"{mag:.3g} Н",
                color='tab:red', fontsize=8, ha='center', va='bottom')

    ax.set_aspect('equal')
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.axis('off')
    ax.set_title('Расчётная схема фермы', fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def draw_forces(truss, forces, path):
    xs = [n.x for n in truss.nodes]
    ys = [n.y for n in truss.nodes]
    pad = max(1.0, 0.15 * (max(xs) - min(xs) + 1))
    fig, ax = plt.subplots(figsize=(9, 6))

    max_abs = max(abs(f) for f in forces) or 1.0
    for m, N in zip(truss.members, forces):
        ni, nj = truss.nodes[m.i], truss.nodes[m.j]
        color = 'tab:red' if N > 1e-6 else ('tab:blue' if N < -1e-6 else '#888')
        lw = 1.2 + 4.5 * abs(N) / max_abs
        ax.plot([ni.x, nj.x], [ni.y, nj.y], color=color, lw=lw, zorder=2,
                solid_capstyle='round')
        xm, ym = (ni.x + nj.x) / 2, (ni.y + nj.y) / 2
        ax.text(xm, ym, f"{N:.3g}", fontsize=7.5, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.75))

    for n in truss.nodes:
        ax.plot(n.x, n.y, 'o', color='#222', ms=5, zorder=3)

    ax.set_aspect('equal')
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.axis('off')
    ax.set_title('Усилия в стержнях N, Н  (красный — растяжение, синий — сжатие)', fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
