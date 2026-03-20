"""
Финансовый трекер на Flask
Учебный проект, неделя 1-2: Базовая настройка
"""
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


@app.route('/')
def home():
    return '<h1>Финансовый трекер</h1><p>Проект в разработке...</p>'


if __name__ == '__main__':
    app.run(debug=True)
