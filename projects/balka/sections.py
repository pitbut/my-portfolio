# -*- coding: utf-8 -*-
"""Геометрические характеристики поперечных сечений."""
import math


def rectangle(b, h):
    # b - ширина, h - высота (м)
    A = b * h
    Ix = b * h ** 3 / 12
    Wx = b * h ** 2 / 6
    return {'A': A, 'Ix': Ix, 'Wx': Wx, 'y_max': h / 2,
            'desc': f"Прямоугольник b×h = {b*1000:.1f}×{h*1000:.1f} мм"}


def circle(d):
    r = d / 2
    A = math.pi * d ** 2 / 4
    Ix = math.pi * d ** 4 / 64
    Wx = math.pi * d ** 3 / 32
    return {'A': A, 'Ix': Ix, 'Wx': Wx, 'y_max': r,
            'desc': f"Круг d = {d*1000:.1f} мм"}


def pipe(d_out, d_in):
    A = math.pi * (d_out ** 2 - d_in ** 2) / 4
    Ix = math.pi * (d_out ** 4 - d_in ** 4) / 64
    Wx = Ix / (d_out / 2)
    return {'A': A, 'Ix': Ix, 'Wx': Wx, 'y_max': d_out / 2,
            'desc': f"Труба (кольцо) D×d = {d_out*1000:.1f}×{d_in*1000:.1f} мм"}


def i_beam(h, b, s, t):
    """Упрощённый двутавр: h - высота, b - ширина полки,
    s - толщина стенки, t - толщина полки (м)."""
    h_w = h - 2 * t
    A = b * h ** 3 - (b - s) * h_w ** 3  # вспом.
    Ix = (b * h ** 3 - (b - s) * h_w ** 3) / 12
    Wx = Ix / (h / 2)
    A_area = b * t * 2 + s * h_w
    return {'A': A_area, 'Ix': Ix, 'Wx': Wx, 'y_max': h / 2,
            'desc': f"Двутавр h×b×s×t = {h*1000:.0f}×{b*1000:.0f}×{s*1000:.1f}×{t*1000:.1f} мм"}


def box(b_out, h_out, t):
    """Прямоугольная замкнутая труба (короб) толщиной стенки t."""
    b_in, h_in = b_out - 2 * t, h_out - 2 * t
    A = b_out * h_out - b_in * h_in
    Ix = (b_out * h_out ** 3 - b_in * h_in ** 3) / 12
    Wx = Ix / (h_out / 2)
    return {'A': A, 'Ix': Ix, 'Wx': Wx, 'y_max': h_out / 2,
            'desc': f"Прямоугольная труба (короб) {b_out*1000:.0f}×{h_out*1000:.0f}×{t*1000:.1f} мм"}


SECTION_BUILDERS = {
    'rectangle': rectangle,
    'circle': circle,
    'pipe': pipe,
    'i_beam': i_beam,
    'box': box,
}
