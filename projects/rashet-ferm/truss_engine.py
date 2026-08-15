# -*- coding: utf-8 -*-
"""
truss_engine.py
Плоская стержневая ферма (шарнирные узлы), метод конечных элементов
(прямой метод жёсткости, стержневой элемент — только осевая жёсткость EA/L).

Почему МКЭ, а не метод узлов/сечений вручную: тот же принцип, что и в
beam_engine.py — одна и та же процедура корректно решает и статически
определимые, и статически неопределимые фермы (лишние стержни/лишние опорные
связи), без отдельной логики для каждого случая. После решения перемещений
узлов усилия в стержнях получаются напрямую (N = EA/L * удлинение),
что эквивалентно результату метода вырезания узлов.

Знаки: N > 0 — растяжение, N < 0 — сжатие.
Оси: x вправо, y вверх.
"""
import numpy as np


class Node:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)


class Member:
    def __init__(self, i, j):
        self.i = i  # индекс узла начала
        self.j = j  # индекс узла конца


class Support:
    def __init__(self, node, kind):
        # kind: 'pin' (шарнирно-неподвижная, ux=uy=0),
        #       'roller_y' (каток на горизонтальной поверхности, uy=0, ux свободен)
        #       'roller_x' (каток на вертикальной поверхности, ux=0, uy свободен)
        self.node = node
        self.kind = kind

    @property
    def label(self):
        return {'pin': 'Шарнирно-неподвижная опора',
                'roller_y': 'Каток (опирание по вертикали)',
                'roller_x': 'Каток (опирание по горизонтали)'}[self.kind]


class Truss:
    def __init__(self, E, A):
        self.E = float(E)          # Па — модуль упругости (общий для всех стержней)
        self.A = float(A)          # м² — площадь сечения стержня (общая для всех)
        self.nodes = []
        self.members = []
        self.supports = []
        self.loads = {}            # node_idx -> (Fx, Fy)

    def add_node(self, x, y):
        self.nodes.append(Node(x, y))
        return len(self.nodes) - 1

    def add_member(self, i, j):
        self.members.append(Member(i, j))

    def add_support(self, node, kind):
        self.supports.append(Support(node, kind))

    def add_load(self, node, fx, fy):
        fx0, fy0 = self.loads.get(node, (0.0, 0.0))
        self.loads[node] = (fx0 + fx, fy0 + fy)

    def member_length(self, m):
        ni, nj = self.nodes[m.i], self.nodes[m.j]
        return ((nj.x - ni.x) ** 2 + (nj.y - ni.y) ** 2) ** 0.5

    def degree_of_determinacy(self):
        """m + r - 2n : 0 => определима, >0 => неопределима (лишние связи),
        <0 => геометрически изменяемая система (механизм)."""
        m = len(self.members)
        n = len(self.nodes)
        r = 0
        for s in self.supports:
            r += 2 if s.kind == 'pin' else 1
        return m + r - 2 * n, m, r, n

    def solve(self):
        n = len(self.nodes)
        ndof = 2 * n
        K = np.zeros((ndof, ndof))
        F = np.zeros(ndof)
        EA = self.E * self.A

        Ls = []
        for m in self.members:
            ni, nj = self.nodes[m.i], self.nodes[m.j]
            dx, dy = nj.x - ni.x, nj.y - ni.y
            L = (dx ** 2 + dy ** 2) ** 0.5
            Ls.append(L)
            if L < 1e-9:
                raise ValueError("Стержень нулевой длины — совпадающие узлы.")
            c, s = dx / L, dy / L
            k = (EA / L) * np.array([
                [c * c, c * s, -c * c, -c * s],
                [c * s, s * s, -c * s, -s * s],
                [-c * c, -c * s, c * c, c * s],
                [-c * s, -s * s, c * s, s * s],
            ])
            dofs = [2 * m.i, 2 * m.i + 1, 2 * m.j, 2 * m.j + 1]
            for a in range(4):
                for b in range(4):
                    K[dofs[a], dofs[b]] += k[a, b]

        for node, (fx, fy) in self.loads.items():
            F[2 * node] += fx
            F[2 * node + 1] += fy

        fixed = []
        for s in self.supports:
            if s.kind == 'pin':
                fixed += [2 * s.node, 2 * s.node + 1]
            elif s.kind == 'roller_y':
                fixed += [2 * s.node + 1]
            elif s.kind == 'roller_x':
                fixed += [2 * s.node]
        fixed = sorted(set(fixed))
        free = [d for d in range(ndof) if d not in fixed]

        if not free:
            raise ValueError("Все узлы закреплены — задача вырождена.")

        Kff = K[np.ix_(free, free)]
        Ff = F[free]
        try:
            d_free = np.linalg.solve(Kff, Ff)
        except np.linalg.LinAlgError:
            raise ValueError(
                "Система стержней и опор геометрически изменяема (механизм) — "
                "ферма неустойчива. Проверьте число и расположение стержней/опор."
            )

        d = np.zeros(ndof)
        d[free] = d_free

        R_full = K.dot(d) - F
        reactions = []
        for s in self.supports:
            reactions.append({
                'node': s.node, 'kind': s.kind,
                'Rx': R_full[2 * s.node] if s.kind in ('pin', 'roller_x') else 0.0,
                'Ry': R_full[2 * s.node + 1] if s.kind in ('pin', 'roller_y') else 0.0,
            })

        forces = []
        for m, L in zip(self.members, Ls):
            ni, nj = self.nodes[m.i], self.nodes[m.j]
            dx, dy = nj.x - ni.x, nj.y - ni.y
            c, s = dx / L, dy / L
            ui, vi = d[2 * m.i], d[2 * m.i + 1]
            uj, vj = d[2 * m.j], d[2 * m.j + 1]
            elong = (uj - ui) * c + (vj - vi) * s
            N = EA / L * elong
            forces.append(N)

        self._d = d
        self._reactions = reactions
        self._forces = forces
        self._Ls = Ls
        return reactions, forces

    def check_equilibrium(self):
        sumFx = sum(f['Rx'] for f in self._reactions) + sum(fx for fx, fy in self.loads.values())
        sumFy = sum(f['Ry'] for f in self._reactions) + sum(fy for fx, fy in self.loads.values())
        return sumFx, sumFy
