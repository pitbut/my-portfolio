# -*- coding: utf-8 -*-
"""
Flask-приложение "Расчёт фермы" (модуль для сайта).
Роуты:
  GET  /                -> интерфейс конструктора фермы
  POST /api/calculate   -> JSON: реакции, усилия в стержнях, проверки, картинки (base64)
  POST /api/report      -> генерирует .docx записку и отдаёт файл на скачивание
"""
import base64
import io
import os
import tempfile
import traceback

from flask import Flask, request, jsonify, send_file, render_template

from truss_engine import Truss
import sections
import diagrams
import report

app = Flask(__name__)

STEEL_E = 2.0e11
DEFAULT_SIGMA_ALLOW = 160e6


def _build_truss(data):
    E = float(data.get('E', STEEL_E))
    sec_type = data['section']['type']
    dims_mm = data['section']['dims']
    dims = {k: float(v) / 1000.0 for k, v in dims_mm.items()}
    sec = sections.SECTION_BUILDERS[sec_type](**dims)

    truss = Truss(E=E, A=sec['A'])
    nodes_in = data.get('nodes', [])
    members_in = data.get('members', [])
    supports_in = data.get('supports', [])
    loads_in = data.get('loads', [])

    if len(nodes_in) < 2:
        raise ValueError("Нужно минимум 2 узла.")
    if not members_in:
        raise ValueError("Добавьте хотя бы один стержень.")
    if not supports_in:
        raise ValueError("Добавьте хотя бы одну опору.")

    for nd in nodes_in:
        truss.add_node(float(nd['x']), float(nd['y']))
    for mb in members_in:
        i, j = int(mb['i']), int(mb['j'])
        if i == j or not (0 <= i < len(nodes_in)) or not (0 <= j < len(nodes_in)):
            raise ValueError(f"Некорректный стержень {i}-{j}.")
        truss.add_member(i, j)
    for s in supports_in:
        truss.add_support(int(s['node']), s['kind'])
    for ld in loads_in:
        truss.add_load(int(ld['node']), float(ld.get('fx', 0.0)), float(ld.get('fy', 0.0)))

    return truss, sec, dims, sec_type, loads_in


def _png_b64(path):
    with open(path, 'rb') as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode('ascii')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    data = request.get_json(force=True)
    try:
        truss, sec, dims, sec_type, loads_in = _build_truss(data)
        deg, m, r, n = truss.degree_of_determinacy()
        if deg < 0:
            raise ValueError(
                f"Система — механизм (m + r − 2n = {deg} < 0): "
                f"{m} стержней, {r} опорных связей, {n} узлов. Добавьте стержни или опоры."
            )
        reactions, forces = truss.solve()
        sfx, sfy = truss.check_equilibrium()

        I_min = sections.min_moment_of_inertia(sec_type, dims)
        sigma_allow = float(data.get('sigma_allow', DEFAULT_SIGMA_ALLOW))
        E = truss.E

        member_checks = []
        worst_ratio = 0.0
        for i, (mb, N) in enumerate(zip(truss.members, forces)):
            L = truss.member_length(mb)
            sigma = N / sec['A']
            if N >= 0:
                ratio = abs(sigma) / sigma_allow if sigma_allow > 0 else 0
                ncr = None
            else:
                import math
                ncr = math.pi ** 2 * E * I_min / L ** 2
                ratio = abs(N) / ncr if ncr > 0 else 1e9
            worst_ratio = max(worst_ratio, ratio)
            member_checks.append({
                'i': i, 'nodes': [mb.i, mb.j], 'N': N, 'sigma_MPa': sigma / 1e6,
                'Ncr': ncr, 'ratio': ratio,
            })

        with tempfile.TemporaryDirectory() as tmp:
            p_scheme = os.path.join(tmp, 'scheme.png')
            p_forces = os.path.join(tmp, 'forces.png')
            diagrams.draw_scheme(truss, loads_in, p_scheme)
            diagrams.draw_forces(truss, forces, p_forces)
            images = {k: _png_b64(p) for k, p in [('scheme', p_scheme), ('forces', p_forces)]}

        return jsonify({
            'ok': True,
            'determinacy': {'deg': deg, 'm': m, 'r': r, 'n': n},
            'reactions': reactions,
            'forces': forces,
            'member_checks': member_checks,
            'equilibrium': [sfx, sfy],
            'sigma_allow_MPa': sigma_allow / 1e6,
            'section': {'A': sec['A'], 'I_min': I_min, 'desc': sec['desc']},
            'all_ok': bool(worst_ratio <= 1.0),
            'images': images,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 400


@app.route('/api/report', methods=['POST'])
def api_report():
    data = request.get_json(force=True)
    try:
        truss, sec, dims, sec_type, loads_in = _build_truss(data)
        deg, m, r, n = truss.degree_of_determinacy()
        if deg < 0:
            raise ValueError("Система — механизм, расчёт невозможен.")
        truss.solve()
        I_min = sections.min_moment_of_inertia(sec_type, dims)
        sigma_allow = float(data.get('sigma_allow', DEFAULT_SIGMA_ALLOW))

        with tempfile.TemporaryDirectory() as tmp:
            p_scheme = os.path.join(tmp, 'scheme.png')
            p_forces = os.path.join(tmp, 'forces.png')
            diagrams.draw_scheme(truss, loads_in, p_scheme)
            diagrams.draw_forces(truss, truss._forces, p_forces)

            ctx = {
                'author': data.get('author', ''),
                'date': data.get('date', ''),
                'truss': truss,
                'loads_in': loads_in,
                'section': sec,
                'E': truss.E,
                'I_min': I_min,
                'sigma_allow': sigma_allow,
                'images': {'scheme': p_scheme, 'forces': p_forces},
            }
            out_path = os.path.join(tmp, 'truss_report.docx')
            report.generate_report(ctx, out_path)
            buf = io.BytesIO()
            with open(out_path, 'rb') as fh:
                buf.write(fh.read())
            buf.seek(0)

        return send_file(buf, as_attachment=True, download_name='Расчёт_фермы.docx',
                          mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5060)
