**1. Foundational Models**

Створити таблицю з принаймні 10 foundational models (proprietary та open-weights) як ти хочеш спробувати у своїй роботі. Коротко зазнач чому саме ця модель.

Для кожної моделі зібрати ключові інженерні параметри:

- Назва моделі та провайдер
- Тип (Proprietary / Open-weights)
- Context Window (розмір контекстного вікна)
- Ціна (Input/Output за 1M токенів)
- Модальності (Text, Vision, Audio, Video)
- Tool Calling (підтримка викликів інструментів вендором)


**2. Embeddings models**

Знайти та виписати параметри для 3 популярних моделей ембедінгів:

- Dimensions: Довжина вектора (1536, 1024?)
- Max Input Tokens: Обсяг тексту для одного вектора
- MTEB Score: Місце в Massive Text Embedding Benchmark
- Ціна/Хостинг: Вартість або можливість локального запуску

Приклади моделей: text-embedding-3-small, multilingual-e5-large, cohere-embed-v3


**3. Chatbot Arena: Models comparison**

Зайти на LMSYS Chatbot Arena(https://arena.ai/text) і поставити 3 складних логічних питання двом анонімним моделям.

Моделі приховані — ти не знаєш які саме.

Результат: записати у файл

- Три питання які ти ставив
- Які ключові відмінності у відповідях обох моделей(яку відповідь ти обрав і чому)
- Зазнач які це були моделі
