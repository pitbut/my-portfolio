# -*- coding: utf-8 -*-
"""Пример: балка на 3 опорах с силой, моментом и распределённой нагрузкой."""
from beam_engine import Beam
import sections
import diagrams
import report

E = 2.0e11  # Па, сталь
beam = Beam(length=8.0, E=E, I=0.0)

supports_in = [
    {'x': 0.0, 'kind': 'pin'},
    {'x': 3.0, 'kind': 'roller'},
    {'x': 8.0, 'kind': 'fixed'},
]
forces_in = [{'x': 5.0, 'value': -8000.0}]
moments_in = [{'x': 6.5, 'value': 3000.0}]
dloads_in = [{'x1': 0.0, 'x2': 3.0, 'value1': -2000.0, 'value2': -2000.0}]

for s in supports_in:
    beam.add_support(s['x'], s['kind'])
for f in forces_in:
    beam.add_force(f['x'], f['value'])
for m in moments_in:
    beam.add_moment(m['x'], m['value'])
for d in dloads_in:
    beam.add_dload(d['x1'], d['x2'], d['value1'], d['value2'])

sec = sections.rectangle(0.12, 0.20)
beam.I = sec['Ix']

reactions = beam.solve_reactions()
segs = beam.segments()
print("Reactions:", reactions)

diagrams.draw_scheme(beam, forces_in, moments_in, dloads_in, "/home/claude/beam_calc/samples/scheme.png")
xs, Qs, Ms = beam.sample(400)
diagrams.draw_epure(xs, Qs, "/home/claude/beam_calc/samples/Q.png", "Эпюра Q(x)", "Q, Н", "tab:blue")
diagrams.draw_epure(xs, Ms, "/home/claude/beam_calc/samples/M.png", "Эпюра M(x)", "M, Н·м", "tab:red")
diagrams.draw_deflection(beam, "/home/claude/beam_calc/samples/defl.png")

n_unknown = sum((2 if s['kind'] == 'fixed' else 1) for s in supports_in)
determinate = (n_unknown <= 3)

ctx = {
    'author': 'Пример',
    'date': '28.07.2026',
    'beam': beam,
    'forces_in': forces_in,
    'moments_in': moments_in,
    'dloads_in': dloads_in,
    'section': sec,
    'E': E,
    'sigma_allow': 160e6,
    'deflection_ratio': 250,
    'determinate': determinate,
    'images': {
        'scheme': "/home/claude/beam_calc/samples/scheme.png",
        'Q': "/home/claude/beam_calc/samples/Q.png",
        'M': "/home/claude/beam_calc/samples/M.png",
        'defl': "/home/claude/beam_calc/samples/defl.png",
    },
}

report.generate_report(ctx, "/home/claude/beam_calc/samples/report_demo.docx")
print("OK, report generated")
