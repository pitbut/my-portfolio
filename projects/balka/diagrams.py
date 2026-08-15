# -*- coding: utf-8 -*-
"""Построение рисунков: расчётная схема балки, эпюры Q и M."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


def _draw_support(ax, x, kind, y0=0):
    s = 0.35
    if kind == 'fixed':
        ax.plot([x, x], [y0 - s, y0 + s], color='k', lw=3)
        for k in range(6):
            yy = y0 - s + k * (2 * s / 5)
            ax.plot([x, x - 0.18], [yy, yy - 0.18], color='k', lw=1)
    else:
        tri = patches.Polygon([[x - s * 0.6, y0 - s], [x + s * 0.6, y0 - s], [x, y0]],
                               closed=True, fill=False, lw=1.6, edgecolor='k')
        ax.add_patch(tri)
        if kind == 'roller':
            ax.plot([x - s * 0.6, x + s * 0.6], [y0 - s - 0.08, y0 - s - 0.08], color='k', lw=1.6)


def draw_scheme(beam, forces_in, moments_in, dloads_in, path):
    L = beam.L
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.plot([0, L], [0, 0], color='k', lw=4, solid_capstyle='butt', zorder=3)

    for s in beam.supports:
        _draw_support(ax, s.x, s.kind)

    for f in forces_in:
        x, val = f['x'], f['value']
        up = val > 0
        y0, y1 = (0.9, 0.05) if up else (-0.05, -0.9)
        ax.annotate('', xy=(x, y1 if up else y1), xytext=(x, y0),
                    arrowprops=dict(arrowstyle='-|>', color='tab:red', lw=2))
        ax.text(x, (y0 + (0.15 if up else -0.15)), f"{abs(val):.3g} Н", color='tab:red',
                ha='center', fontsize=9, va='bottom' if up else 'top')

    for m in moments_in:
        x, val = m['x'], m['value']
        ccw = val > 0
        theta = np.linspace(0.3, 2.6, 30) if ccw else np.linspace(2.6, 0.3, 30)
        r = 0.35
        ax.plot(x + r * np.cos(theta), 0.4 * np.sign(1) + r * np.sin(theta) * 0 + r * np.sin(theta),
                color='tab:blue', lw=1.8)
        arr_i = -1 if ccw else 0
        ax.annotate('', xy=(x + r * np.cos(theta[arr_i]), r * np.sin(theta[arr_i])),
                     xytext=(x + r * np.cos(theta[arr_i - 1]), r * np.sin(theta[arr_i - 1])),
                     arrowprops=dict(arrowstyle='-|>', color='tab:blue', lw=1.8))
        ax.text(x, r + 0.2, f"{abs(val):.3g} Н·м", color='tab:blue', ha='center', fontsize=9)

    for d in dloads_in:
        x1, x2, w1, w2 = d['x1'], d['x2'], d['value1'], d['value2']
        n = 7
        xs = np.linspace(x1, x2, n)
        top = 0.6
        sign = 1 if (w1 + w2) >= 0 else -1
        ax.plot([x1, x2], [top * sign, top * sign], color='tab:orange', lw=1.4)
        for xx in xs:
            ax.annotate('', xy=(xx, 0.03 * sign), xytext=(xx, top * sign),
                        arrowprops=dict(arrowstyle='-|>', color='tab:orange', lw=1.2))
        ax.text((x1 + x2) / 2, top * sign + 0.18 * sign,
                f"q = {abs(w1):.3g}" + (f"…{abs(w2):.3g}" if w1 != w2 else "") + " Н/м",
                color='tab:orange', ha='center', fontsize=9)

    for xt in sorted({0.0, L} | {s.x for s in beam.supports}):
        ax.text(xt, -1.25, f"{xt:.2f} м", ha='center', fontsize=8, color='dimgray')

    ax.set_xlim(-0.6, L + 0.6)
    ax.set_ylim(-1.5, 1.5)
    ax.axis('off')
    ax.set_title('Расчётная схема балки', fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def draw_epure(xs, ys, path, title, ylabel, color, fmt='{:.2f}'):
    fig, ax = plt.subplots(figsize=(9, 2.6))
    ax.plot(xs, ys, color=color, lw=1.8)
    ax.fill_between(xs, ys, 0, color=color, alpha=0.18)
    ax.axhline(0, color='k', lw=1)
    i_max = int(np.argmax(ys))
    i_min = int(np.argmin(ys))
    for i in {i_max, i_min}:
        ax.plot([xs[i]], [ys[i]], 'o', color=color, ms=4)
        ax.annotate(fmt.format(ys[i]), (xs[i], ys[i]), textcoords="offset points",
                    xytext=(0, 8 if ys[i] >= 0 else -14), ha='center', fontsize=8)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel('x, м')
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def draw_deflection(beam, path):
    xs = np.linspace(0, beam.L, 300)
    ys = np.array([beam.deflection(x) * 1000 for x in xs])  # мм
    draw_epure(xs, ys, path, 'Эпюра прогибов v(x)', 'v, мм', 'tab:green', fmt='{:.3f}')
