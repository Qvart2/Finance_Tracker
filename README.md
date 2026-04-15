# Финансовый трекер

Веб-приложение для учёта личных финансов на Flask.

## Возможности

- **Транзакции**: добавление, редактирование и удаление доходов/расходов
- **Категории**: создание цветных категорий для классификации транзакций
- **Бюджеты**: месячные лимиты на категории расходов с отслеживанием остатка
- **Статистика**: сводка доходов, расходов и текущего баланса
- **Авторизация**: регистрация и вход пользователей, изолированные данные

## Стек

- Python 3 / Flask
- Flask-SQLAlchemy + SQLite
- Flask-Login, Flask-WTF
- Jinja2, HTML/CSS/JS (без сторонних UI-фреймворков)

## Установка и запуск

```bash
git clone https://github.com/Qvart2/Finance_Tracker.git
cd Finance_Tracker

python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

pip install -r requirements.txt
python app.py
```

Приложение будет доступно по адресу: http://localhost:5000

## Конфигурация

Секретный ключ Flask задаётся через переменную окружения `SECRET_KEY`.  
Без неё приложение использует дефолтный ключ, подходящий только для локальной разработки.

```bash
export SECRET_KEY="ваш-секретный-ключ"   # Linux/Mac
set SECRET_KEY=ваш-секретный-ключ        # Windows
```

## Структура проекта

```
Finance_Tracker/
├── app.py              # Основной файл приложения (модели, формы, маршруты)
├── requirements.txt    # Зависимости Python
├── .gitignore
├── instance/
│   └── finance.db      # База данных SQLite (создаётся автоматически)
└── templates/
    ├── base.html               # Базовый шаблон с навигацией и CSS
    ├── login.html              # Страница входа
    ├── register.html           # Страница регистрации
    ├── dashboard.html          # Главная панель с транзакциями
    ├── transaction_form.html   # Форма добавления/редактирования транзакции
    ├── categories.html         # Список категорий
    ├── category_form.html      # Форма категории
    ├── budgets.html            # Список бюджетов
    └── budget_form.html        # Форма бюджета
```
