# Прогресс

Статусы: `todo` / `done`.

| Неделя | День | Задача | Статус | Код | Видео |
|--------|------|--------|--------|-----|-------|
| 01 | 01 | Первый запрос к LLM через API (Telegram-бот на Gemini) | done | [week-01/day-01](../week-01/day-01/) | [▶](https://www.loom.com/share/45330da8e4494e6ca49480a3420ff787) |
| 01 | 02 | Формат ответа: сравнение без/с ограничениями (формат, длина, stop) | done | [week-01/day-02](../week-01/day-02/) | [▶](https://www.loom.com/share/866d3823571646c698e02f7b201d084b) |
| 01 | 03 | Разные способы рассуждения: 4 метода (прямой / пошагово / meta / эксперты) на задаче-ловушке «автомойка» | done | [week-01/day-03](../week-01/day-03/) | [▶](https://www.loom.com/share/20f5f9c908834b5581588171f83c1cc2) |
| 01 | 04 | Температура: сравнение 0/0.7/1.2 (+1.5/2.0) по точности/креативности/разнообразию; конвейер выбора слова + эксперимент top_p/top_k | done | [week-01/day-04](../week-01/day-04/) | [▶](https://www.loom.com/share/70d345242d1446a8ada8343cbc50eb83) |
| 01 | 05 | Версии моделей: 1 промпт-ловушка на 4 GPT (3.5/4o/4.1/o3), замер latency/токенов/₽; эксперимент «точность промпта × сила модели» | done | [week-01/day-05](../week-01/day-05/) | [▶](https://www.loom.com/share/80198dddfa8644c5b92ebf0823304d0c) |
| 02 | 06 | Первый агент: iOS-приложение AgentChat (SwiftUI), мульти-агент (Аладдин/Акс/Шут) поверх ProxyAPI, память, фото, выбор моделей | done | [week-02/day-06](../week-02/day-06/) · [AgentChat](../AgentChat/) | [▶](https://drive.google.com/file/d/1oxYBNidlMzq5eve09l61oSuv6t2t1pWy/view?usp=sharing) |
| 02 | 07 | Сохранение контекста: SQLite (SwiftData) + слоистая память — долгие факты между сессиями, сжатие в summary, JSON-экспорт | done | [week-02/day-07](../week-02/day-07/) · [AgentChat](../AgentChat/) | [▶](https://www.loom.com/share/f35016674e984ab6a81f10998e507ba0) |
| 02 | 08 | Токены и контекстное окно: подсчёт токенов (вход/выход/итого + ₽), рост стоимости, стриминг (SSE), компактация в summary, демонстрация поломки при переполнении | done | [week-02/day-08](../week-02/day-08/) · [AgentChat](../AgentChat/) | [▶](https://www.loom.com/share/2f4052d188a34c45a730ead89fb72a7e) |
| 02 | 09 | Сжатие истории: окно последних N + старое в summary (отдельно, подставляется вместо полной истории), тумблер сжатия для сравнения качества/токенов без и со сжатием | done | [week-02/day-09](../week-02/day-09/) · [AgentChat](../AgentChat/) | [▶](https://www.loom.com/share/cbeff47284d641ad913540f47d3b14e1) |
| 02 | 10 | Управление контекстом: 3 стратегии без summary (Sliding Window / Sticky Facts KV / Branching) как 3 тест-агента; раздел «Мои \| Тестовые»; ветки с форком/переключением/удалением | done | [week-02/day-10](../week-02/day-10/) · [AgentChat](../AgentChat/) | [▶](https://www.loom.com/share/2383219a98a4483cb535fb2230070678) |
| 03 | 11 | Модель памяти: 3 слоя (краткосрочная / рабочая / долговременная), авто-извлечение, MemorySheet UI | done | [week-03/day-11](../week-03/day-11/) · [AgentChat](../AgentChat/) | [▶](https://www.loom.com/share/448df13307fd48d991a8dd3fd7d1da4a) |
| 03 | 12 | Персонализация: слоистый профиль юзера (стиль/правила/стек), подключение к каждому запросу, 2 профиля → разные ответы | done | [agent-cli](../agent-cli/) | [▶](https://www.loom.com/share/46f41dfce33b4181bed14f6802d003f3) |
| 03 | 13 | Task State Machine: 4 стадии-агента (planning→execution→validation→done), детерминированные переходы, пауза/resume | done | [agent-cli](../agent-cli/) | [▶](https://www.loom.com/share/e516f7eb3f634c52b6870968d3103ac2) |
| 03 | 14 | Инварианты: правила отдельно от диалога, инжект в промпт, проверка код+LLM, отказ нарушать | done | [agent-cli](../agent-cli/) | [▶](https://www.loom.com/share/216ee8cfa37f404087023ccd88672676) |
| 04 | 15 | Контролируемые переходы: рой 3 агентов (PLANNING) + Оркестратор-надсмотрщик на всех стадиях, именованные сессии SQLite с персистом, `/session` команды, `/task jump` FSM-демо | done | [agent-cli](../agent-cli/) | todo |

> **Пивот (день 12+):** переходим с iOS (`AgentChat/`) на CLI/TUI на Python (`agent-cli/`).
> AgentChat остаётся, не удаляем. Причина: недели 4–7 (MCP/RAG/VPS/пайплайны) iOS не тянет.
