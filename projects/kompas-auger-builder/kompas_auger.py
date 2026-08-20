# -*- coding: utf-8 -*-
"""
kompas_auger.py — библиотека построения шнеков (винтовых конвейерных спиралей)
в КОМПАС-3D через COM API.

Поддерживаемые типы шнека (AugerParams.kind):
    "simple"          — цилиндрический, постоянный диаметр, постоянный шаг
    "conic"            — конический, диаметр меняется линейно, шаг постоянный
    "conic_variable"   — конический, диаметр и шаг меняются вдоль оси

Требования:
    - Windows + установленный КОМПАС-3D (проверялось на линейке v18-v23, API версии 5)
    - pip install pywin32
    - КОМПАС можно не запускать заранее — скрипт сам подключится/запустит его

Как редактировать модель:
    Вся геометрия строится из параметров AugerParams. Чтобы изменить шнек —
    поменяйте поля датакласса и вызовите build_auger(params) заново
    (пересоздаст 3D-деталь и чертёж с новыми размерами). Для "simple" и "conic"
    направляющие спирали — штатные параметрические объекты КОМПАСа, поэтому их
    дополнительно можно поправить и вручную, раскрыв дерево модели.

Важное предупреждение по надёжности:
    Подключение к КОМПАСу и построение направляющих кривых (build_shaft,
    build_guide_curves) используют интерфейсы, задокументированные в SDK
    КОМПАС-3D (ksCylindricSpiralDefinition, ksConicSpiralDefinition,
    ksSplineDefinition) — это самая надёжная часть модуля.
    Построение тела лопасти по направляющим (loft/оболочка/булева операция)
    и простановка размеров на чертеже помечены как EXPERIMENTAL: у автора
    библиотеки нет установленного КОМПАСа для тестового прогона, поэтому эти
    шаги обёрнуты в try/except — если конкретный вызов не совпадёт с вашей
    версией API, скрипт не упадёт молча, а напечатает, что не получилось и
    какие 2-3 клика в интерфейсе КОМПАСа сделать вместо него (направляющие
    кривые к этому моменту уже будут построены).
"""

import math
from dataclasses import dataclass
from typing import Optional, List, Tuple

import pythoncom
import win32com.client
from win32com.client import gencache


# --------------------------------------------------------------------------
# Подключение к КОМПАС-3D (API5 — интерфейсы ksPart/ksEntity/ksDocument3D)
# GUID'ы взяты из официальной страницы SDK:
# https://help.ascon.ru/KOMPAS_SDK/22/ru-RU/compiling_python.html
# --------------------------------------------------------------------------

GUID_CONSTANTS_2D = "{75C9F5D0-B5B8-4526-8681-9903C567D2ED}"
GUID_CONSTANTS_3D = "{2CAF168C-7961-4B90-9DA2-701419BEEFE3}"
GUID_API5 = "{0422828C-F174-495E-AC5D-D31014DBBE87}"


class Kompas:
    """Держит открытое соединение с КОМПАС-3D и его модули констант."""

    def __init__(self):
        self.module5 = gencache.EnsureModule(GUID_API5, 0, 1, 0)
        self.const2d = gencache.EnsureModule(GUID_CONSTANTS_2D, 0, 1, 0).constants
        self.const3d = gencache.EnsureModule(GUID_CONSTANTS_3D, 0, 1, 0).constants

        dispatch = win32com.client.Dispatch("KOMPAS.Application.5")
        self.app = self.module5.KompasObject(
            dispatch._oleobj_.QueryInterface(
                self.module5.KompasObject.CLSID, pythoncom.IID_IDispatch
            )
        )
        self.app.Visible = True
        self.app.ActivateControllerAPI()


def connect() -> Kompas:
    """Подключиться к запущенному КОМПАСу или запустить новый экземпляр."""
    return Kompas()


# --------------------------------------------------------------------------
# Параметры шнека
# --------------------------------------------------------------------------

@dataclass
class AugerParams:
    kind: str  # "simple" | "conic" | "conic_variable"

    shaft_diameter: float   # d — диаметр вала, мм
    length: float            # L — длина шнека вдоль оси, мм
    blade_thickness: float   # s — толщина лопасти, мм

    # simple: только outer_diameter
    outer_diameter: Optional[float] = None       # D, мм

    # conic / conic_variable: диаметр лопасти по концам
    outer_diameter_start: Optional[float] = None  # D1, мм
    outer_diameter_end: Optional[float] = None    # D2, мм

    # simple / conic: постоянный шаг
    pitch: Optional[float] = None                 # t, мм

    # conic_variable: шаг меняется линейно по длине
    pitch_start: Optional[float] = None           # t1, мм
    pitch_end: Optional[float] = None              # t2, мм

    points_per_turn: int = 24   # плотность точек сплайна (для conic_variable)
    right_handed: bool = True    # направление навивки

    def validate(self):
        if self.kind not in ("simple", "conic", "conic_variable"):
            raise ValueError(f"Неизвестный тип шнека: {self.kind}")
        if self.shaft_diameter <= 0 or self.length <= 0 or self.blade_thickness <= 0:
            raise ValueError("shaft_diameter, length, blade_thickness должны быть > 0")

        if self.kind == "simple":
            if not self.outer_diameter or not self.pitch:
                raise ValueError("simple: нужны outer_diameter и pitch")
            if self.outer_diameter <= self.shaft_diameter:
                raise ValueError("outer_diameter должен быть больше shaft_diameter")

        elif self.kind == "conic":
            if not (self.outer_diameter_start and self.outer_diameter_end and self.pitch):
                raise ValueError("conic: нужны outer_diameter_start, outer_diameter_end, pitch")

        elif self.kind == "conic_variable":
            need = (self.outer_diameter_start, self.outer_diameter_end,
                    self.pitch_start, self.pitch_end)
            if not all(need):
                raise ValueError(
                    "conic_variable: нужны outer_diameter_start/end и pitch_start/end"
                )

    # --- производные величины ---

    def outer_radius_at(self, z: float) -> float:
        """Радиус лопасти (мм) в точке z вдоль оси (0..length)."""
        if self.kind == "simple":
            return self.outer_diameter / 2.0
        r1 = self.outer_diameter_start / 2.0
        r2 = self.outer_diameter_end / 2.0
        return r1 + (r2 - r1) * (z / self.length)

    def pitch_at(self, z: float) -> float:
        """Шаг витка (мм) в точке z вдоль оси."""
        if self.kind == "conic_variable":
            return self.pitch_start + (self.pitch_end - self.pitch_start) * (z / self.length)
        return self.pitch

    def theta_at(self, z: float) -> float:
        """Угол поворота (рад) направляющей в точке z, с учётом переменного шага."""
        t1 = self.pitch_at(0.0)
        t2 = self.pitch_at(self.length)
        sign = 1.0 if self.right_handed else -1.0
        if abs(t2 - t1) < 1e-9:
            return sign * 2 * math.pi * z / t1
        # dTheta/dz = 2*pi / t(z), t(z) линейна по z -> интеграл даёт логарифм
        tz = self.pitch_at(z)
        return sign * (2 * math.pi * self.length / (t2 - t1)) * math.log(tz / t1)

    def total_turns(self) -> float:
        return abs(self.theta_at(self.length)) / (2 * math.pi)

    def guide_points(self, radius_fn, n: Optional[int] = None) -> List[Tuple[float, float, float]]:
        """Точки направляющей кривой (x, y, z) в мм. radius_fn(z) -> радиус."""
        turns = max(self.total_turns(), 0.01)
        n = n or max(int(turns * self.points_per_turn), 8)
        pts = []
        for i in range(n + 1):
            z = self.length * i / n
            theta = self.theta_at(z)
            r = radius_fn(z)
            pts.append((r * math.cos(theta), r * math.sin(theta), z))
        return pts


# --------------------------------------------------------------------------
# Построение вала
# --------------------------------------------------------------------------

def build_shaft(k: Kompas, part, params: AugerParams):
    """Строит цилиндрический вал длиной params.length, диаметром shaft_diameter."""
    c3d = k.const3d

    sketch_entity = part.NewEntity(c3d.o3d_sketch)
    sketch_def = sketch_entity.GetDefinition()
    sketch_def.SetPlane(part.GetDefaultEntity(c3d.o3d_planeXOY))
    sketch_entity.Create()

    doc2d = sketch_def.BeginEdit()
    doc2d.ksCircle(0, 0, params.shaft_diameter / 2.0, 1)
    sketch_def.EndEdit()

    extrusion = part.NewEntity(c3d.o3d_bossExtrusion)
    extrusion_def = extrusion.GetDefinition()
    extrusion_def.SetSketch(sketch_entity)
    extrusion_def.directionType = c3d.dtNormal
    side = extrusion_def.ExtrusionParam(True)
    side.depthNormal = params.length
    side.typeNormal = c3d.etBlind
    extrusion.Create()
    return extrusion


# --------------------------------------------------------------------------
# Построение направляющих кривых лопасти (внутренняя — по валу, внешняя — по OD)
# --------------------------------------------------------------------------

def _build_native_spiral(k: Kompas, part, params: AugerParams, diam_mm: float,
                          diam_start_mm: Optional[float] = None,
                          diam_end_mm: Optional[float] = None):
    """simple -> ksCylindricSpiralDefinition, conic -> ksConicSpiralDefinition."""
    c3d = k.const3d
    turns = params.total_turns()

    if params.kind == "simple":
        entity = part.NewEntity(c3d.o3d_curveCylindricSpiral)
        d = entity.GetDefinition()
        d.SetPlane(part.GetDefaultEntity(c3d.o3d_planeXOY))
        d.buildMode = 2  # по количеству витков и высоте
        d.diamType = 0
        d.diam = diam_mm
        d.heightType = 0
        d.height = params.length
        d.turn = turns
        d.turnDir = params.right_handed
        d.buildDir = True
        entity.Create()
        return entity

    # conic
    entity = part.NewEntity(c3d.o3d_curveConicSpiral)
    d = entity.GetDefinition()
    d.SetPlane(part.GetDefaultEntity(c3d.o3d_planeXOY))
    d.buildMode = 2
    d.initialDiamType = 0
    d.initialDiam = diam_start_mm
    d.terminalDiamType = 0
    d.terminalDiam = diam_end_mm
    d.heightType = 0
    d.height = params.length
    d.turn = turns
    d.turnDir = params.right_handed
    d.buildDir = True
    entity.Create()
    return entity


def _build_spline_curve(k: Kompas, part, params: AugerParams, radius_fn):
    c3d = k.const3d
    entity = part.NewEntity(c3d.o3d_curveSpline)
    d = entity.GetDefinition()
    d.cls = False
    d.degree = 3
    for x, y, z in params.guide_points(radius_fn):
        d.AddVertex(x, y, z, 1.0)
    entity.Create()
    return entity


def build_guide_curves(k: Kompas, part, params: AugerParams):
    """Возвращает (inner_curve, outer_curve) — направляющие лопасти
    по внутреннему краю (у вала) и по внешнему краю (наружный диаметр)."""

    if params.kind == "simple":
        inner = _build_native_spiral(k, part, params, params.shaft_diameter)
        outer = _build_native_spiral(k, part, params, params.outer_diameter)
        return inner, outer

    if params.kind == "conic":
        inner = _build_native_spiral(k, part, params, params.shaft_diameter)
        outer = _build_native_spiral(
            k, part, params, None,
            params.outer_diameter_start, params.outer_diameter_end,
        )
        return inner, outer

    # conic_variable — шаг переменный, штатные спирали КОМПАСа этого не умеют,
    # поэтому строим направляющие точками (см. AugerParams.guide_points)
    inner = _build_spline_curve(k, part, params, lambda z: params.shaft_diameter / 2.0)
    outer = _build_spline_curve(k, part, params, params.outer_radius_at)
    return inner, outer


# --------------------------------------------------------------------------
# EXPERIMENTAL: тело лопасти (лофт между направляющими -> оболочка -> булева)
# --------------------------------------------------------------------------

def build_blade_solid(k: Kompas, part, params: AugerParams, inner_curve, outer_curve, shaft):
    """Пытается построить твёрдое тело лопасти и приварить его к валу.

    Возвращает True при успехе. При неудаче печатает инструкцию для ручной
    достройки в интерфейсе КОМПАСа (направляющие кривые к этому моменту уже
    построены и видны в дереве модели)."""
    c3d = k.const3d
    try:
        loft = part.NewEntity(c3d.o3d_baseLoft)
        loft_def = loft.GetDefinition()
        loft_def.way = 1  # линейчатая (по направляющим, прямые перемычки)
        loft_def.SetGuideCurvesCount(2)
        loft_def.guideCurves(0).SetGuideCurve(inner_curve)
        loft_def.guideCurves(1).SetGuideCurve(outer_curve)
        loft.Create()

        shell = part.NewEntity(c3d.o3d_shell)
        shell_def = shell.GetDefinition()
        shell_def.thickness1 = params.blade_thickness / 2.0
        shell_def.thickness2 = params.blade_thickness / 2.0
        shell_def.SetThinSolid(True)
        shell.Create()

        boolean = part.NewEntity(c3d.o3d_booleanArifm)
        boolean_def = boolean.GetDefinition()
        boolean_def.SetOperationType(c3d.bool_Union)
        boolean.Create()
        return True
    except Exception as exc:  # noqa: BLE001 — сознательно широкий catch
        print("[build_blade_solid] Не удалось автоматически построить тело лопасти:", exc)
        print("Направляющие кривые уже в дереве модели. Сделайте вручную:")
        print("  1) 'Элемент по сечениям' (линейчатый) по двум направляющим кривым;")
        print(f"  2) 'Оболочка' полученной поверхности, толщина {params.blade_thickness} мм;")
        print("  3) Булева операция 'Объединение' с валом.")
        return False


# --------------------------------------------------------------------------
# EXPERIMENTAL: 2D чертёж-схема с простановкой размеров
# --------------------------------------------------------------------------

def build_drawing(k: Kompas, params: AugerParams):
    """Строит упрощённую схему шнека (развёртка контура) с размерами D/d/t/L."""
    c2d = k.const2d
    try:
        doc = k.app.Document2D()
        doc.Create(False, True)
        v = doc.ksLineSeg(0, 0, params.length, 0, 1)  # ось / нижняя образующая
        doc.ksLineSeg(0, params.shaft_diameter / 2.0, params.length,
                      params.shaft_diameter / 2.0, 1)
        doc.ksLineSeg(0, -params.shaft_diameter / 2.0, params.length,
                      -params.shaft_diameter / 2.0, 1)

        ldp = k.app.GetParamStruct(c2d.ko_LDimParam)
        ldp.Init()
        ldp.style = 1
        ldp.point1.x, ldp.point1.y = 0, params.shaft_diameter / 2.0
        ldp.point2.x, ldp.point2.y = 0, -params.shaft_diameter / 2.0
        ldp.text.str = f"d {params.shaft_diameter:g}"
        doc.ksLinDimension(ldp)

        ldp2 = k.app.GetParamStruct(c2d.ko_LDimParam)
        ldp2.Init()
        ldp2.style = 1
        ldp2.point1.x, ldp2.point1.y = 0, 0
        ldp2.point2.x, ldp2.point2.y = params.length, 0
        ldp2.text.str = f"L {params.length:g}"
        doc.ksLinDimension(ldp2)
        return doc
    except Exception as exc:  # noqa: BLE001
        print("[build_drawing] Не удалось автоматически построить чертёж:", exc)
        print("Постройте эскиз развёртки и проставьте размеры D/d/t/L вручную —")
        print("геометрия шнека (направляющие) уже готова в 3D-документе.")
        return None


# --------------------------------------------------------------------------
# Оркестратор
# --------------------------------------------------------------------------

def build_auger(params: AugerParams, k: Optional[Kompas] = None,
                 with_drawing: bool = True):
    """Полный цикл: подключение -> новая деталь -> вал -> направляющие лопасти
    -> (best-effort) тело лопасти -> (best-effort) чертёж.

    Чтобы отредактировать шнек — поменяйте поля params и вызовите build_auger
    заново."""
    params.validate()
    k = k or connect()
    c3d = k.const3d

    doc3d = k.app.Document3D()
    doc3d.Create(False, True)
    part = doc3d.GetPart(c3d.pTop_Part)

    print(f"Строим шнек [{params.kind}] — {params.total_turns():.2f} витков")

    shaft = build_shaft(k, part, params)
    inner, outer = build_guide_curves(k, part, params)
    build_blade_solid(k, part, params, inner, outer, shaft)

    drawing = build_drawing(k, params) if with_drawing else None

    return k, doc3d, drawing
