# -*- coding: utf-8 -*-
from truss_engine import Truss
import sections
import diagrams
import report

E = 2.0e11
truss = Truss(E=E, A=0.0)

# простая ферма-треугольник с дополнительными панелями (statically determinate Pratt-like)
coords = [(0,0), (2,0), (4,0), (6,0), (8,0), (2,2), (4,2), (6,2)]
for x, y in coords:
    truss.add_node(x, y)

members = [
    (0,1), (1,2), (2,3), (3,4),      # нижний пояс
    (5,6), (6,7),                     # верхний пояс
    (0,5), (5,2), (2,6), (6,4), (4,7), (7,3),  # раскосы/стойки
    (1,5), (3,7),
]
for i, j in members:
    truss.add_member(i, j)

truss.add_support(0, 'pin')
truss.add_support(4, 'roller_y')

loads_in = [
    {'node': 1, 'fx': 0.0, 'fy': -5000.0},
    {'node': 2, 'fx': 0.0, 'fy': -8000.0},
    {'node': 3, 'fx': 0.0, 'fy': -5000.0},
]
for ld in loads_in:
    truss.add_load(ld['node'], ld['fx'], ld['fy'])

sec_type = 'pipe'
dims = {'d_out': 0.06, 'd_in': 0.05}
sec = sections.SECTION_BUILDERS[sec_type](**dims)
truss.A = sec['A']

deg, m, r, n = truss.degree_of_determinacy()
print('determinacy:', deg, m, r, n)

reactions, forces = truss.solve()
print('reactions:', reactions)
print('forces:', forces)
print('equilibrium check:', truss.check_equilibrium())

diagrams.draw_scheme(truss, loads_in, "/home/claude/truss_calc/samples/scheme.png")
diagrams.draw_forces(truss, forces, "/home/claude/truss_calc/samples/forces.png")

I_min = sections.min_moment_of_inertia(sec_type, dims)

ctx = {
    'author': 'Пример',
    'date': '29.07.2026',
    'truss': truss,
    'loads_in': loads_in,
    'section': sec,
    'E': E,
    'I_min': I_min,
    'sigma_allow': 160e6,
    'images': {
        'scheme': "/home/claude/truss_calc/samples/scheme.png",
        'forces': "/home/claude/truss_calc/samples/forces.png",
    },
}
report.generate_report(ctx, "/home/claude/truss_calc/samples/report_demo.docx")
print("OK")
