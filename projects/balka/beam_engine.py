# -*- coding: utf-8 -*-
"""
beam_engine.py
Универсальный решатель балки методом конечных элементов (метод перемещений,
балочный КЭ Эйлера-Бернулли, 2 узла x 2 СС на узел: прогиб v и угол поворота theta).

Почему МКЭ, а не "классические" уравнения равновесия:
  - работает одинаково и для статически ОПРЕДЕЛИМЫХ, и для статически
    НЕОПРЕДЕЛИМЫХ балок (до 4 опор включительно, любые комбинации шарнир/заделка)
    без отдельной логики метода сил / трёх моментов;
  - после решения жёсткостной задачи внутренние усилия Q(x), M(x) находятся
    классическим методом сечений (это и попадает в пояснительную записку).

Оси: x вправо (0..L), y вверх.
Знаки: сила вверх — положительная; момент против часовой стрелки (CCW) — положительный.
Эпюра Q(x): сумма проекций всех сил слева от сечения на ось y.
Эпюра M(x): сумма моментов всех сил/пар слева от сечения относительно сечения
            (изгибающий момент положителен, если растянуты нижние волокна — "балка
            прогибается выпуклостью вниз", стандартное правило знаков сопромата).
"""
import numpy as np


class Support:
    def __init__(self, x, kind):
        # kind: 'pin' (шарнирно-неподвижная), 'roller' (шарнирно-подвижная),
        #       'fixed' (жёсткая заделка)
        self.x = float(x)
        self.kind = kind

    @property
    def restrains_v(self):
        return True

    @property
    def restrains_theta(self):
        return self.kind == 'fixed'

    @property
    def label(self):
        return {'pin': 'Шарнирно-неподвижная опора',
                'roller': 'Шарнирно-подвижная опора',
                'fixed': 'Жёсткая заделка'}[self.kind]


class PointForce:
    def __init__(self, x, value):
        # value: Н, положительное значение = вверх, отрицательное = вниз
        self.x = float(x)
        self.value = float(value)


class PointMoment:
    def __init__(self, x, value):
        # value: Н*м, положительное = против часовой стрелки (CCW)
        self.x = float(x)
        self.value = float(value)


class DistributedLoad:
    def __init__(self, x1, x2, w1, w2=None):
        # w1, w2: Н/м, положительное = вверх, отрицательное = вниз
        # если w2 не задан — равномерная нагрузка w1; иначе — линейно меняющаяся (трапеция)
        self.x1 = float(x1)
        self.x2 = float(x2)
        self.w1 = float(w1)
        self.w2 = float(w2) if w2 is not None else float(w1)

    def w_at(self, x):
        if self.x2 == self.x1:
            return 0.0
        t = (x - self.x1) / (self.x2 - self.x1)
        return self.w1 + (self.w2 - self.w1) * t

    def resultant(self):
        R = 0.5 * (self.w1 + self.w2) * (self.x2 - self.x1)
        if self.w1 == self.w2:
            xc = 0.5 * (self.x1 + self.x2)
        else:
            # центр тяжести трапеции
            L = self.x2 - self.x1
            if abs(self.w1 + self.w2) < 1e-12:
                xc = 0.5 * (self.x1 + self.x2)
            else:
                xc = self.x1 + L * (self.w1 + 2 * self.w2) / (3 * (self.w1 + self.w2))
        return R, xc


class Beam:
    def __init__(self, length, E, I):
        self.L = float(length)
        self.E = float(E)
        self.I = float(I)
        self.supports = []
        self.forces = []
        self.moments = []
        self.dloads = []

    def add_support(self, x, kind):
        self.supports.append(Support(x, kind))

    def add_force(self, x, value):
        self.forces.append(PointForce(x, value))

    def add_moment(self, x, value):
        self.moments.append(PointMoment(x, value))

    def add_dload(self, x1, x2, w1, w2=None):
        self.dloads.append(DistributedLoad(x1, x2, w1, w2))

    # ---------- breakpoints / mesh ----------
    def _breakpoints(self, refine=1):
        pts = {0.0, self.L}
        for s in self.supports:
            pts.add(round(s.x, 9))
        for f in self.forces:
            pts.add(round(f.x, 9))
        for m in self.moments:
            pts.add(round(m.x, 9))
        for d in self.dloads:
            pts.add(round(d.x1, 9))
            pts.add(round(d.x2, 9))
        pts = sorted(p for p in pts if -1e-9 <= p <= self.L + 1e-9)
        if refine <= 1:
            return pts
        out = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            if b - a < 1e-9:
                continue
            for k in range(1, refine + 1):
                out.append(a + (b - a) * k / refine)
        return out

    # ---------- FEM stiffness solve for reactions ----------
    def solve_reactions(self):
        nodes = self._breakpoints(refine=1)
        n = len(nodes)
        ndof = 2 * n
        K = np.zeros((ndof, ndof))
        F = np.zeros(ndof)
        E, I = self.E, self.I

        def kmat(Le):
            c = E * I / Le ** 3
            return c * np.array([
                [12, 6 * Le, -12, 6 * Le],
                [6 * Le, 4 * Le ** 2, -6 * Le, 2 * Le ** 2],
                [-12, -6 * Le, 12, -6 * Le],
                [6 * Le, 2 * Le ** 2, -6 * Le, 4 * Le ** 2],
            ])

        idx_of = {round(x, 9): i for i, x in enumerate(nodes)}

        for e in range(n - 1):
            x1, x2 = nodes[e], nodes[e + 1]
            Le = x2 - x1
            if Le < 1e-9:
                continue
            ke = kmat(Le)
            dofs = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
            for a in range(4):
                for b in range(4):
                    K[dofs[a], dofs[b]] += ke[a, b]

            # эквивалентные узловые нагрузки от распределённой нагрузки на участке
            w1 = w2 = 0.0
            for d in self.dloads:
                lo, hi = max(d.x1, x1), min(d.x2, x2)
                if hi - lo > 1e-9:
                    w1 += d.w_at(x1)
                    w2 += d.w_at(x2)
            if abs(w1) > 1e-12 or abs(w2) > 1e-12:
                # консистентные узловые нагрузки (эрмитовы функции формы),
                # линейная нагрузка w(s)=w1+(w2-w1)*s/Le, s из [0, Le]
                # (получено интегрированием N_i(s)*w(s) по элементу)
                Fv1 = Le * (7 * w1 + 3 * w2) / 20
                M1 = Le ** 2 * (3 * w1 + 2 * w2) / 60
                Fv2 = Le * (3 * w1 + 7 * w2) / 20
                M2 = -Le ** 2 * (2 * w1 + 3 * w2) / 60
                F[dofs[0]] += Fv1
                F[dofs[1]] += M1
                F[dofs[2]] += Fv2
                F[dofs[3]] += M2

        for pf in self.forces:
            i = idx_of[round(pf.x, 9)]
            F[2 * i] += pf.value
        for pm in self.moments:
            i = idx_of[round(pm.x, 9)]
            F[2 * i + 1] += pm.value

        # граничные условия
        fixed_dofs = []
        for s in self.supports:
            i = idx_of[round(s.x, 9)]
            fixed_dofs.append(2 * i)
            if s.restrains_theta:
                fixed_dofs.append(2 * i + 1)
        fixed_dofs = sorted(set(fixed_dofs))
        free_dofs = [d for d in range(ndof) if d not in fixed_dofs]

        if len(free_dofs) == 0:
            raise ValueError("Балка полностью защемлена везде — задача вырождена.")

        Kff = K[np.ix_(free_dofs, free_dofs)]
        Ff = F[free_dofs]
        try:
            d_free = np.linalg.solve(Kff, Ff)
        except np.linalg.LinAlgError:
            raise ValueError(
                "Система опор не обеспечивает геометрическую неизменяемость балки "
                "(механизм). Нужно минимум 2 точки опирания или заделка."
            )

        d = np.zeros(ndof)
        d[free_dofs] = d_free

        R_full = K.dot(d) - F  # реакции = усилия связей
        reactions = []
        for s in self.supports:
            i = idx_of[round(s.x, 9)]
            Rv = R_full[2 * i]
            Rm = R_full[2 * i + 1] if s.restrains_theta else 0.0
            reactions.append({'x': s.x, 'kind': s.kind, 'R': Rv, 'M': Rm})

        self._nodes = nodes
        self._d = d
        self._reactions = reactions
        return reactions

    # ---------- сегментные аналитические формулы Q(x), M(x) ----------
    def segments(self):
        """Возвращает список сегментов между breakpoints с коэффициентами
        Q(x) = Q0 + w*(x-x0)
        M(x) = M0 + Q0*(x-x0) + w*(x-x0)^2/2
        (w — суммарная действующая на участке равномерная составляющая;
         для трапеций используется среднее значение участка, если он не делится)."""
        if not hasattr(self, '_reactions'):
            self.solve_reactions()
        nodes = self._breakpoints(refine=1)

        # точечные силы = приложенные + реакции опор (в узлах)
        point_forces = {}
        for f in self.forces:
            point_forces[round(f.x, 9)] = point_forces.get(round(f.x, 9), 0.0) + f.value
        for r in self._reactions:
            point_forces[round(r['x'], 9)] = point_forces.get(round(r['x'], 9), 0.0) + r['R']

        point_moments = {}
        for m in self.moments:
            point_moments[round(m.x, 9)] = point_moments.get(round(m.x, 9), 0.0) + m.value
        for r in self._reactions:
            if abs(r['M']) > 1e-9:
                point_moments[round(r['x'], 9)] = point_moments.get(round(r['x'], 9), 0.0) + r['M']

        segs = []
        Q0, M0 = 0.0, 0.0
        for i in range(len(nodes) - 1):
            x0, x1 = nodes[i], nodes[i + 1]
            key0 = round(x0, 9)
            Q0 += point_forces.get(key0, 0.0)
            M0 -= point_moments.get(key0, 0.0)
            # действующая распределённая нагрузка на этом участке (может быть трапецией)
            w0 = 0.0
            w1 = 0.0
            for d in self.dloads:
                if d.x1 - 1e-9 <= x0 and x1 <= d.x2 + 1e-9:
                    w0 += d.w_at(x0)
                    w1 += d.w_at(x1)
            Le = x1 - x0
            if Le < 1e-9:
                continue
            slope = (w1 - w0) / Le if Le > 1e-9 else 0.0
            segs.append({
                'x0': x0, 'x1': x1, 'Q0': Q0, 'M0': M0, 'w0': w0, 'w1': w1, 'slope': slope
            })
            Q1 = Q0 + 0.5 * (w0 + w1) * Le
            M1 = M0 + Q0 * Le + w0 * Le ** 2 / 2 + slope * Le ** 3 / 6
            Q0, M0 = Q1, M1
        # добавим точечную силу/момент в последнем узле (для проверки ~0 на конце свободного конца)
        key_last = round(nodes[-1], 9)
        Q0 += point_forces.get(key_last, 0.0)
        M0 -= point_moments.get(key_last, 0.0)
        self._end_Q, self._end_M = Q0, M0
        self._segs = segs
        return segs

    def Q(self, x):
        for seg in self._segs:
            if seg['x0'] - 1e-9 <= x <= seg['x1'] + 1e-9:
                dx = x - seg['x0']
                return seg['Q0'] + seg['w0'] * dx + seg['slope'] * dx ** 2 / 2
        return 0.0

    def M(self, x):
        for seg in self._segs:
            if seg['x0'] - 1e-9 <= x <= seg['x1'] + 1e-9:
                dx = x - seg['x0']
                return seg['M0'] + seg['Q0'] * dx + seg['w0'] * dx ** 2 / 2 + seg['slope'] * dx ** 3 / 6
        return 0.0

    def sample(self, n=400):
        xs = np.linspace(0, self.L, n)
        Qs = np.array([self.Q(x) for x in xs])
        Ms = np.array([self.M(x) for x in xs])
        return xs, Qs, Ms

    def deflection(self, x):
        """Прогиб v(x) интерполяцией функциями формы Эрмита по узлам МКЭ."""
        nodes = self._nodes
        for i in range(len(nodes) - 1):
            x0, x1 = nodes[i], nodes[i + 1]
            if x0 - 1e-9 <= x <= x1 + 1e-9:
                Le = x1 - x0
                s = (x - x0) / Le if Le > 1e-9 else 0.0
                v1, t1, v2, t2 = self._d[2 * i], self._d[2 * i + 1], self._d[2 * i + 2], self._d[2 * i + 3]
                N1 = 1 - 3 * s ** 2 + 2 * s ** 3
                N2 = Le * (s - 2 * s ** 2 + s ** 3)
                N3 = 3 * s ** 2 - 2 * s ** 3
                N4 = Le * (-s ** 2 + s ** 3)
                return N1 * v1 + N2 * t1 + N3 * v2 + N4 * t2
        return 0.0

    def max_abs_Q(self):
        xs, Qs, Ms = self.sample(800)
        i = np.argmax(np.abs(Qs))
        return xs[i], Qs[i]

    def max_abs_M(self):
        xs, Qs, Ms = self.sample(800)
        i = np.argmax(np.abs(Ms))
        return xs[i], Ms[i]
