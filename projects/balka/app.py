# -*- coding: utf-8 -*-
"""
Flask-приложение "Расчёт балки" (модуль для сайта).
Роуты:
  GET  /                -> интерфейс конструктора балки
  POST /api/calculate   -> JSON: реакции, эпюры (как base64 PNG), проверки прочности/жёсткости
  POST /api/report      -> генерирует .docx записку и отдаёт файл на скачивание
"""
import base64
import io
import os
import tempfile
import traceback

from flask import Flask, request, jsonify, send_file, render_template

from beam_engine import Beam
import sections
import diagrams
import report

app = Flask(__name__)

STEEL_E = 2.0e11          # Па, модуль упругости стали (по умолчанию)
DEFAULT_SIGMA_ALLOW = 160e6  # Па (160 МПа — типовое значение для Ст3)


def _build_beam(data):
    L = float(data['length'])
    E = float(data.get('E', STEEL_E))

    sec_type = data['section']['type']
    dims = {k: float(v) / 1000.0 for k, v in data['section']['dims'].items()}  # мм -> м
    sec = sections.SECTION_BUILDERS[sec_type](**dims)

    beam = Beam(length=L, E=E, I=sec['Ix'])

    supports_in = data.get('supports', [])
    forces_in = data.get('forces', [])
    moments_in = data.get('moments', [])
    dloads_in = data.get('dloads', [])

    if not (1 <= len(supports_in) <= 4):
        raise ValueError("Число опор должно быть от 1 до 4.")

    for s in supports_in:
        beam.add_support(float(s['x']), s['kind'])
    for f in forces_in:
        beam.add_force(float(f['x']), float(f['value']))
    for m in moments_in:
        beam.add_moment(float(m['x']), float(m['value']))
    for d in dloads_in:
        beam.add_dload(float(d['x1']), float(d['x2']), float(d['value1']),
                        float(d.get('value2', d['value1'])))

    return beam, sec, supports_in, forces_in, moments_in, dloads_in


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
        beam, sec, supports_in, forces_in, moments_in, dloads_in = _build_beam(data)
        reactions = beam.solve_reactions()
        beam.segments()

        n_unknown = sum((2 if s['kind'] == 'fixed' else 1) for s in supports_in)
        determinate = n_unknown <= 3

        xq, Qmax = beam.max_abs_Q()
        xm, Mmax = beam.max_abs_M()
        sigma_allow = float(data.get('sigma_allow', DEFAULT_SIGMA_ALLOW))
        sigma_max = abs(Mmax) / sec['Wx']
        n_safety = sigma_allow / sigma_max if sigma_max > 0 else None

        with tempfile.TemporaryDirectory() as tmp:
            p_scheme = os.path.join(tmp, 'scheme.png')
            p_Q = os.path.join(tmp, 'Q.png')
            p_M = os.path.join(tmp, 'M.png')
            p_D = os.path.join(tmp, 'D.png')
            diagrams.draw_scheme(beam, forces_in, moments_in, dloads_in, p_scheme)
            xs, Qs, Ms = beam.sample(400)
            diagrams.draw_epure(xs, Qs, p_Q, "Эпюра Q(x)", "Q, Н", "tab:blue")
            diagrams.draw_epure(xs, Ms, p_M, "Эпюра M(x)", "M, Н·м", "tab:red")
            diagrams.draw_deflection(beam, p_D)

            images = {k: _png_b64(p) for k, p in
                      [('scheme', p_scheme), ('Q', p_Q), ('M', p_M), ('defl', p_D)]}

        v_max = max(beam.deflection(x) for x in xs)
        v_min = min(beam.deflection(x) for x in xs)
        v_abs = v_max if abs(v_max) > abs(v_min) else v_min

        return jsonify({
            'ok': True,
            'determinate': determinate,
            'reactions': [{'x': r['x'], 'kind': r['kind'], 'R': r['R'], 'M': r['M']}
                          for r in reactions],
            'Qmax': Qmax, 'xQmax': xq,
            'Mmax': Mmax, 'xMmax': xm,
            'sigma_max_MPa': sigma_max / 1e6,
            'sigma_allow_MPa': sigma_allow / 1e6,
            'safety_factor': n_safety,
            'v_max_mm': v_abs * 1000,
            'section': {'A': sec['A'], 'Ix': sec['Ix'], 'Wx': sec['Wx'], 'desc': sec['desc']},
            'images': images,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 400


@app.route('/api/report', methods=['POST'])
def api_report():
    data = request.get_json(force=True)
    try:
        beam, sec, supports_in, forces_in, moments_in, dloads_in = _build_beam(data)
        beam.solve_reactions()
        beam.segments()

        n_unknown = sum((2 if s['kind'] == 'fixed' else 1) for s in supports_in)
        determinate = n_unknown <= 3
        sigma_allow = float(data.get('sigma_allow', DEFAULT_SIGMA_ALLOW))

        with tempfile.TemporaryDirectory() as tmp:
            p_scheme = os.path.join(tmp, 'scheme.png')
            p_Q = os.path.join(tmp, 'Q.png')
            p_M = os.path.join(tmp, 'M.png')
            p_D = os.path.join(tmp, 'D.png')
            diagrams.draw_scheme(beam, forces_in, moments_in, dloads_in, p_scheme)
            xs, Qs, Ms = beam.sample(400)
            diagrams.draw_epure(xs, Qs, p_Q, "Эпюра Q(x)", "Q, Н", "tab:blue")
            diagrams.draw_epure(xs, Ms, p_M, "Эпюра M(x)", "M, Н·м", "tab:red")
            diagrams.draw_deflection(beam, p_D)

            ctx = {
                'author': data.get('author', ''),
                'date': data.get('date', ''),
                'beam': beam,
                'forces_in': forces_in,
                'moments_in': moments_in,
                'dloads_in': dloads_in,
                'section': sec,
                'E': float(data.get('E', STEEL_E)),
                'sigma_allow': sigma_allow,
                'deflection_ratio': float(data.get('deflection_ratio', 250)),
                'determinate': determinate,
                'images': {'scheme': p_scheme, 'Q': p_Q, 'M': p_M, 'defl': p_D},
            }
            out_path = os.path.join(tmp, 'beam_report.docx')
            report.generate_report(ctx, out_path)

            buf = io.BytesIO()
            with open(out_path, 'rb') as fh:
                buf.write(fh.read())
            buf.seek(0)

        return send_file(buf, as_attachment=True, download_name='Расчёт_балки.docx',
                          mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    except Exception as e:
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5050)
