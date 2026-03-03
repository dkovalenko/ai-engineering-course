# Домашнє завдання: PDF Data Extraction → JSON

## Завдання

У вас є 3 PDF-файли з таблицями футбольних гравців (5 ліг, 7 команд, ~80 гравців).
Кожен PDF має різний формат таблиці — від простого до складного.

Ваша мета:
1. **Реалізувати `extract_text(pdf_path)`** у `starter.py` — витягнути текст з PDF.
2. **Написати промпт** — змінна `PROMPT` у `starter.py`, щоб LLM повертав JSON з плоским списком гравців.

## Файли

| Файл | Складність | Опис |
|------|-----------|------|
| `pdfs/01_split_headers.pdf` | ★☆☆ | Таблиці з розривами між сторінками **без повторення заголовків** |
| `pdfs/02_vertical_header.pdf` | ★★☆ | Назва ліги у **вертикальному лівому стовпці** (merged cell) |
| `pdfs/03_watermark.pdf` | ★★★ | Як `02` + діагональний водяний знак **CONFIDENTIAL** + шумові/частково заповнені рядки |


## Як запустити

```bash
# 1. Встановіть API ключ (OpenRouter)
export OPENROUTER_API_KEY="sk-or-..."

# 2. Запустіть екстракцію (всі PDF)
uv run starter.py

# Або один конкретний файл:
uv run starter.py pdfs/01_split_headers.pdf

# 3. Перевірте результати (всі файли)
uv run eval.py

# Або тільки один файл (швидше для ітерацій):
uv run eval.py 01_split_headers
uv run eval.py 03_watermark
```

## Очікуваний JSON формат

Формат — плоский список гравців:

```json
[
  {
    "league": "Premier League",
    "team": "Arsenal",
    "name": "Bukayo Saka",
    "position": "RW",
    "number": 7,
    "age": 23,
    "nationality": "England",
    "phone": "+44 7123 123456",
    "address": "12 King St, London"
  },
  {
    "league": "La Liga",
    "team": "Real Madrid",
    "name": "Luca Rossi",
    "position": null,
    "number": null,
    "age": null,
    "nationality": null,
    "phone": "7",
    "address": null
  },
  ...
]
```

### Поля гравця

| Поле | Тип | Опис |
|------|-----|------|
| `league` | string | Назва ліги (Premier League, La Liga, Serie A, Bundesliga, Ligue 1) |
| `team` | string | Назва команди |
| `name` | string | Повне ім'я гравця |
| `position` | string | Позиція (GK, CB, RB, LB, CDM, CM, CAM, RW, LW, ST, CF, RWB, LWB) |
| `number` | integer | Номер на футболці |
| `age` | integer | Вік |
| `nationality` | string | Національність |
| `phone` | string | Фейковий номер телефону (може бути `null`) |
| `address` | string | Фейкова адреса (може бути `null`) |

Для частково заповнених рядків (Case 3) поля `position/number/age/nationality/phone/address` можуть бути `null` або відсутні.

## Підказки

- Якщо парсинг JSON падає, подивіться на сирий вивід LLM у консолі — часто модель обгортає JSON у markdown (`` ```json … ``` ``) або додає текст. Можна покращити промпт (наприклад, "Return only JSON, no markdown") або обробити рядок перед парсингом.

## Оцінювання

Скрипт `eval.py` перевіряє:

- **Player count** (40%) — чи знайдено всіх гравців
- **Field accuracy** (60%) — чи правильні значення полів (league, team, name, position, number, age, nationality)

Фінальна оцінка зважена: `split_headers×1 + vertical_header×2 + watermark×3`

| Оцінка | Результат |
|--------|-----------|
| ≥ 95%  | Відмінно |
| ≥ 80%  | Добре |
| ≥ 60%  | Прийнятно |
| < 60%  | Потребує доопрацювання |
