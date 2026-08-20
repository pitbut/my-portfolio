# -*- coding: utf-8 -*-
"""Примеры построения трёх типов шнека библиотекой kompas_auger.

Запускать на Windows с установленным КОМПАС-3D:
    pip install pywin32
    python example.py
"""

from kompas_auger import AugerParams, build_auger, connect


def example_simple(k):
    params = AugerParams(
        kind="simple",
        shaft_diameter=30,
        outer_diameter=200,
        pitch=180,
        length=900,
        blade_thickness=4,
    )
    return build_auger(params, k=k)


def example_conic(k):
    params = AugerParams(
        kind="conic",
        shaft_diameter=30,
        outer_diameter_start=200,
        outer_diameter_end=100,
        pitch=180,
        length=900,
        blade_thickness=4,
    )
    return build_auger(params, k=k)


def example_conic_variable(k):
    params = AugerParams(
        kind="conic_variable",
        shaft_diameter=30,
        outer_diameter_start=200,
        outer_diameter_end=100,
        pitch_start=180,
        pitch_end=90,
        length=900,
        blade_thickness=4,
        points_per_turn=32,
    )
    return build_auger(params, k=k)


if __name__ == "__main__":
    # Одно соединение с КОМПАСом на все три детали:
    k = connect()
    example_simple(k)
    example_conic(k)
    example_conic_variable(k)

    # Чтобы отредактировать — поменяйте параметры выше (или создайте свой
    # AugerParams) и запустите build_auger(params) заново.
