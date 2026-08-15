from flask import Flask, render_template, jsonify, request
import json
import os

app = Flask(__name__)

# Файл для хранения рекордов
SCORES_FILE = 'scores.json'

def load_scores():
    """Загружает рекорды из файла"""
    if os.path.exists(SCORES_FILE):
        try:
            with open(SCORES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_scores(scores):
    """Сохраняет рекорды в файл"""
    try:
        with open(SCORES_FILE, 'w', encoding='utf-8') as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

@app.route('/')
def index():
    """Главная страница с игрой"""
    return render_template('index.html')

@app.route('/api/scores', methods=['GET'])
def get_scores():
    """API для получения рекордов"""
    scores = load_scores()
    # Сортируем по убыванию и берем топ-10
    scores.sort(key=lambda x: x.get('score', 0), reverse=True)
    return jsonify(scores[:10])

@app.route('/api/scores', methods=['POST'])
def add_score():
    """API для добавления нового рекорда"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        name = data.get('name', 'Аноним')[:20]  # Ограничение 20 символов
        score = int(data.get('score', 0))
        
        if score <= 0:
            return jsonify({'error': 'Некорректный счёт'}), 400
        
        scores = load_scores()
        scores.append({
            'name': name,
            'score': score
        })
        
        # Сохраняем только топ-100
        scores.sort(key=lambda x: x.get('score', 0), reverse=True)
        scores = scores[:100]
        
        if save_scores(scores):
            return jsonify({'status': 'success', 'score': score})
        else:
            return jsonify({'error': 'Ошибка сохранения'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Для локального тестирования
    app.run(host='0.0.0.0', port=5000, debug=True)
