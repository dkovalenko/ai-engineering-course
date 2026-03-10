# Домашнє завдання: Eval Pipeline для агента підтримки

## Завдання

У вас є готовий агент підтримки клієнтів **TechStore** (електроніка). Агент має два варіанти системного промпту: **A** (базовий) та **B** (емпатійний). Ваша мета — побудувати **eval pipeline**, щоб об'єктивно порівняти ці два промпти.

Ви **не** пишете агента — ви пишете тести, грейдери та (опціонально) свій промпт, що побиває A і B.

### Що потрібно зробити (4 TODO)

1. **Seed test cases** — додати щонайменше 5 різноманітних тест-кейсів у `SEED_CASES` у `starter.py`.
2. **Code-based grader** — реалізувати функцію `keyword_grader(response, test_case)` у `starter.py`.
3. **LLM-as-Judge rubric** — написати рубрику `JUDGE_RUBRIC` у `starter.py` для оцінки емпатії, якості рішення та професійності (шкала 1–5).
4. **Prompt C (опціонально, але рекомендується)** — написати свій `SYSTEM_PROMPT_C` у `starter.py`, який **перемагає обидва** A і B за вашими ж eval-метриками. Спочатку запустіть A/B, проаналізуйте де вони слабкі — потім покращте промпт і перезапустіть (цикл Eval-Driven Development).

Решта коду (агент, генерація синтетичних тестів, запуск eval, A/B/C порівняння, інтеграція з Langfuse) уже реалізована.

---

## Як запускати

```bash
# 1. API ключ (OpenRouter — для агента та judge)
export OPENROUTER_API_KEY="sk-or-..."

# 2. Швидка перевірка структури домашки (без API викликів)
uv run eval.py

# 3. Запуск eval pipeline (тільки seed-кейси, без синтетики та judge — швидко)
uv run starter.py --quick

# 4. Повний запуск: seed + синтетичні тести + LLM judge
uv run starter.py
```

У повному запуску (`uv run starter.py`) скрипт бере ваші `SEED_CASES` і додатково генерує синтетичні кейси через LLM. Це дає ширше покриття сценаріїв і більш стабільне порівняння промптів (A/B або A/B/C), ніж оцінювання тільки на 5-8 ручних кейсах.

Опціонально для збереження результатів у Langfuse:

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

---

## Схема тест-кейсу (SEED_CASES)

Кожен елемент у `SEED_CASES` — словник з такими полями:

| Поле | Тип | Опис |
|------|-----|------|
| `input` | str | Що пише клієнт (одне повідомлення). |
| `persona` | str | Короткий опис персони (наприклад, "Розлючений клієнт з дефектним товаром"). |
| `category` | str | Категорія сценарію: `defective_product`, `tech_support`, `billing`, `complaint`, `simple_question`, тощо. |
| `expected_tone` | str | Очікуваний тон відповіді: `empathetic`, `professional`, `patient`, тощо. |
| `required_keywords` | list[str] | Ключові слова/фрази, які **мають** з'явитися у відповіді (наприклад, "вибачте", "apologize"). |
| `forbidden_keywords` | list[str] | Фрази, яких **не має** бути (наприклад, "your fault", "not our problem"). |
| `must_offer` | list[str] | Що агент має запропонувати (хоча б одне): "refund", "replacement", "return", "exchange", тощо. |

**Приклад:**

```python
{
    "input": "Замовив ноутбук 3 дні тому, прийшов з тріщиною на екрані!",
    "persona": "Розлючений клієнт з дефектним товаром",
    "category": "defective_product",
    "expected_tone": "empathetic",
    "required_keywords": ["вибачте", "apologize"],
    "forbidden_keywords": ["your fault", "not our problem"],
    "must_offer": ["refund", "replacement", "return"],
}
```

Порада: зробіть кейси різними за категоріями (дефект, техпідтримка, оплата, скарга, просте питання, VIP, ескалація).

---

## Підказки по TODO

### TODO 1: Seed test cases

- Різні `category` — щоб eval не був заточений під один тип запитів.
- `required_keywords` і `forbidden_keywords` мають бути реалістичними: те, що можна автоматично перевірити по тексту відповіді.
- Для tech support / складних клієнтів можна очікувати `patient` або `empathetic` та відповідні ключові слова.

### TODO 2: keyword_grader

- Повертайте словник з ключами: `required_keywords`, `forbidden_keywords`, `must_offer`.
- Кожне значення — float від 0 до 1 (частка виконаних умов).
- Порівняння краще робити без урахування регістру (`.lower()`). Можна враховувати часткове входження підрядка (наприклад, "apologize" в "We apologize").

### TODO 3: JUDGE_RUBRIC

- Рубрика має бути текстом для LLM, який отримує `{input}`, `{response}`, `{expected_tone}` і повертає **тільки** JSON з ключами: `empathy`, `solution_quality`, `professionalism`, `reasoning`.
- Чітко опишіть шкалу 1–5 для кожного критерію (що означає 1, 3, 5).
- Вкажіть у рубриці: "Return ONLY valid JSON, no markdown."

### TODO 4: SYSTEM_PROMPT_C (ваш промпт, що перемагає A і B)

- **Спочатку** виконайте TODO 1–3 і запустіть `uv run starter.py --quick`. Подивіться таблицю A/B: на яких метриках A або B слабкі?
- Подивіться вивід по кейсах: де `Keywords` або `Forbidden` низькі? Де judge ставить низькі бали?
- Напишіть `SYSTEM_PROMPT_C` так, щоб явно виправляти ці слабкості: більше empathy, чіткіші пропозиції (refund/replacement), заборона blamed phrases, структурована відповідь (acknowledge → options → next step).
- Після зміни промпту знову запустіть `uv run starter.py --quick` — побачите таблицю A/B/C і колонку "Best". Ітеруйте, поки C не виграє за більшістю метрик.

---

## Оцінювання

1. **Структурна перевірка**: `uv run eval.py` має проходити (5+ кейсів, різні категорії, grader повертає коректний словник, рубрика без "TODO").
2. **Здати**: скріншот або текст виводу порівняння (A/B або A/B/C) після `uv run starter.py` (або `uv run starter.py --quick`) + короткий висновок у 2–3 речення: який промпт кращий за метриками і чому.
3. **Опціонально (основний виклик)**: здати з заповненим Prompt C і скріншотом A/B/C, де ваш промпт перемагає за більшістю метрик.
4. **Опціонально (бонус)**: скріншот дашборду Langfuse з результатами eval run.

---

## Файли

| Файл | Призначення |
|------|-------------|
| `starter.py` | Основний файл — ваші 4 TODO. Запуск pipeline: `uv run starter.py`. |
| `eval.py` | Перевірка готовності домашки (структура, без API). |
