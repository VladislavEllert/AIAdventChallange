# Неделя 1 — День 1

## Задание

Минимальный код, который шлёт запрос в LLM через API (**ProxyAPI**),
получает ответ и выводит его в консоль (CLI).

## Формат сдачи

**Видео + код. Видео важнее кода.**

## Технические детали

- API: ProxyAPI, OpenAI-совместимый.
- base_url: `https://openai.api.proxyapi.ru/v1`
- Auth: `Authorization: Bearer <PROXYAPI_KEY>` (ключ из `.env`).
- Модель: `gemini-2.5-flash-lite`.

## Установка

```bash
cd week-01/day-01
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# ключ: в корне репо скопируй .env.example -> .env и впиши PROXYAPI_KEY
```

> `python-dotenv` ищет `.env` в текущей папке и выше — корневой `.env` подхватится.

## Запуск

```bash
python main.py "Привет, кто ты?"
python main.py "Напиши хайку про код" --temperature 1.0
python main.py "2+2?" --temperature 0 --max-tokens 50
echo "Объясни рекурсию" | python main.py
```

Флаги под задачу недели (дёргать параметры): `--temperature`, `--top-p`,
`--top-k`, `--max-tokens`, `--seed`, `--system`, `--model`.
Расход токенов печатается в stderr.

## Статус

`todo` — код написан, ждёт ключ ProxyAPI для проверки + запись видео.
