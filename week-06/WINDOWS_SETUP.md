# WINDOWS_SETUP.md — Runbook для Windows-сессии (RTX 4060, 8GB)

> **СТАТУС: выполнено (2026-07-11).** Все шаги пройдены, сервисы подняты и проверены с LAN. Реальные
> отличия от плана ниже, актуальные данные — для Mac-сессии, которая пилит код `agent-web`.
>
> - **Модели:** только `qwen3:4b` (2.5GB). `qwen3:8b` скачивалась, но **удалена** — решили не тащить
>   (место на SSD + не будет использоваться). Голосом юзер называл их «Gemma»/«Qwen2.5» — это
>   опечатка распознавания речи, реально в Ollama всегда были только теги `qwen3:*`.
> - **LAN-IP этого ПК:** `192.168.0.33`.
> - **Endpoint'ы (все проверены curl'ом с самого Windows по LAN-IP, не localhost):**
>   ```
>   OLLAMA_CHAT_URL=http://192.168.0.33:11434/v1
>   COMFYUI_URL=http://192.168.0.33:8188
>   METRICS_URL=http://192.168.0.33:11435/metrics
>   ```
> - **Метрик-агент готов (день 29):** `week-06/metrics_server.py` написан и живьём проверен на маке
>   (CPU/RAM реальные, GPU/VRAM/nvidia-smi/ollama_models — код есть, но НЕ проверен на самом Windows,
>   т.к. эта Mac-сессия не имеет туда терминального доступа. На Windows нужно: `pip install psutil`,
>   затем `python week-06\metrics_server.py`, проверить `curl http://localhost:11435/metrics`
>   возвращает реальные `gpu_pct`/`vram_used_gb` (не `null`) — если `null`, значит `nvidia-smi` не
>   на PATH, разобраться отдельно.
> - **Firewall:** 3 правила созданы вручную юзером через elevated PowerShell (агент не может пройти
>   UAC в неинтерактивной сессии) — `Ollama 11434`, `ComfyUI 8188`, `Metrics 11435`.
> - **Гочта с pip:** на этом ПК системный SOCKS-прокси в `HKCU\...\Internet Settings`
>   (`ProxyServer=socks=127.0.0.1:10808`, от VPN-софта) — `pip` из коробки падает с
>   `Missing dependencies for SOCKS support`. Фикс — гонять pip через PowerShell с явно
>   очищенными `$env:HTTP_PROXY=""`/`$env:HTTPS_PROXY=""`. `git`/`curl` эту проблему не имели.
> - **VRAM-реальность:** SDXL 1024×1024, 20 steps, `--lowvram` — влезло в 8GB, ~4.9GB под
>   модель+VAE+CLIP пиково, генерация ~44с (первый прогон, холодная загрузка чекпоинта в VRAM).
>   Одновременно с Qwen3-4B в Ollama не проверяли совместную нагрузку — на дне 29/30 замерить честно.
> - **API-workflow:** экспортирован и закоммичен —
>   `agent-web/agent_web/services/comfyui_workflows/sdxl.json`. Ноды: `4`=CheckpointLoaderSimple,
>   `6`=positive CLIPTextEncode, `7`=negative CLIPTextEncode, `3`=KSampler (seed/steps/cfg сюда
>   подставлять), `5`=EmptyLatentImage (width/height), `9`=SaveImage.
> - **Запуск ComfyUI:** `venv\Scripts\python main.py --listen 0.0.0.0 --port 8188 --lowvram` из
>   `C:\GitRepos\ComfyUI`. Не сервис — процесс живёт пока открыт терминал/фон. Автозапуска нет,
>   при перезагрузке Windows нужно поднимать заново вручную (или задать через Task Scheduler —
>   не делали, не просили).
> - **Ollama LAN:** `OLLAMA_HOST=0.0.0.0` записан в `setx` (переживёт релогин/ребут), но при
>   ручном перезапуске приложения (не через логин) переменную нужно явно передавать процессу —
>   через explorer/автозапуск подхватывается из реестра, через ручной `cmd /c start` — нет.
>
> Мониторинг GPU на Windows: `nvidia-smi` в терминале, либо Диспетчер задач → Производительность →
> GPU (там же VRAM/Copy/3D графики), либо `Get-Counter` для скриптовой проверки.

---

> **Это исполняемый runbook.** Открой Claude Code в этой сессии (репозиторий склонирован на Windows-ПК)
> и скажи: «выполни week-06/WINDOWS_SETUP.md». Агент пройдёт шаги по порядку, проверяя каждый реальной
> командой терминала.
>
> **Цель:** поднять на этом Windows-ПК три сетевых сервиса, доступных с MacBook по локальной сети:
> - **Ollama** (текстовые LLM: Qwen3 8B, Qwen3 4B) — порт **11434**
> - **ComfyUI** (генерация картинок: SDXL) — порт **8188**
> - **Метрик-агент** (CPU/RAM/GPU/VRAM) — порт **11435**
>
> В конце — отдать пользователю LAN-IP и строку для `.env` на маке.

---

## ПРАВИЛА АГЕНТУ (обязательно)

1. **Думай пошагово.** Один шаг — одна проверка. Не прыгай вперёд.
2. **НЕ ВРАТЬ, НЕ ВЫДУМЫВАТЬ.** Версии, теги моделей, имена файлов, структуру ComfyUI API — проверять **реальными командами** (`ollama list`, `curl`, `nvidia-smi`), не по памяти. Не уверен — скажи «не уверен», не гадай.
3. **Всё проверять терминалом.** После каждой установки — команда-проверка + показать вывод. Провал — чинить, не замалчивать.
4. **8GB VRAM — узкое место.** Замерять реальное потребление (`ollama ps`, `nvidia-smi`), не обещать «всё влезет».
5. **Ничего деструктивного** без подтверждения. Не удалять чужие модели/данные.

---

## ШАГ 1. GPU / драйвер

```powershell
nvidia-smi
```
- Должна показать RTX 4060, версию драйвера, VRAM ~8GB. Нет `nvidia-smi` → поставить актуальный NVIDIA-драйвер, потом продолжить.
- Записать: total VRAM (для расчётов дальше).

---

## ШАГ 2. Ollama — установка и проверка

```powershell
ollama --version
```
- **Нет** → установить: `winget install Ollama.Ollama` (или установщик с ollama.com). После — перезапустить терминал, повторить `ollama --version`.
- **Есть** → дальше.

---

## ШАГ 3. Текстовые модели (Qwen3 8B + 4B)

```powershell
ollama list
```
Если нет нужных — скачать (**сверить точные теги** — Qwen3 вышел, но тег уточнить живым pull; если `qwen3:8b` не тянется, глянуть `ollama.com/library/qwen3` и взять корректный):
```powershell
ollama pull qwen3:8b
ollama pull qwen3:4b
```
Проверить ответ:
```powershell
ollama run qwen3:4b "Скажи одно слово: привет"
```
- Непустой осмысленный ответ = ок.

---

## ШАГ 4. Открыть Ollama по сети (LAN)

По умолчанию Ollama слушает только localhost. Нужно `0.0.0.0`:
```powershell
setx OLLAMA_HOST "0.0.0.0"
```
- **Перезапустить сервис Ollama** (выйти из трея и запустить снова, либо перелогиниться) — `setx` применяется к новым процессам.
- Firewall-правило на порт 11434 (PowerShell **от админа**):
```powershell
New-NetFirewallRule -DisplayName "Ollama 11434" -Direction Inbound -Protocol TCP -LocalPort 11434 -Action Allow
```
Проверка локально:
```powershell
curl http://localhost:11434/api/tags
```
Записать LAN-IP:
```powershell
ipconfig
```
- Взять IPv4 активного адаптера (обычно `192.168.x.x`). **Записать — отдать пользователю.**

---

## ШАГ 5. ComfyUI — установка и проверка

Проверить, стоит ли (каталог ComfyUI / запускается ли). Если **нет** — установить:
```powershell
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
(Если нет подходящего PyTorch с CUDA — поставить по инструкции с сайта ComfyUI/PyTorch под CUDA версии драйвера. **Сверить, не гадать.**)

---

## ШАГ 6. SDXL-чекпоинт

Скачать SDXL base в `ComfyUI/models/checkpoints/`.
- Файл: `sd_xl_base_1.0.safetensors` (~6.6GB) с официального репозитория Stability (HuggingFace `stabilityai/stable-diffusion-xl-base-1.0`). **Проверить актуальную ссылку/имя перед скачиванием.**
- Положить в `ComfyUI/models/checkpoints/`.

---

## ШАГ 7. Запустить ComfyUI по сети

```powershell
python main.py --listen 0.0.0.0 --port 8188 --lowvram
```
- `--lowvram`/`--medvram` — под 8GB (замерить `nvidia-smi` что реально грузится; если хватает без флага — убрать).
- Firewall на 8188 (от админа):
```powershell
New-NetFirewallRule -DisplayName "ComfyUI 8188" -Direction Inbound -Protocol TCP -LocalPort 8188 -Action Allow
```
Проверка:
1. Открыть `http://localhost:8188` в браузере.
2. Сгенерить **тестовую картинку** дефолтным workflow (SDXL checkpoint, простой промпт) — убедиться что GPU работает, картинка выходит.
3. **Экспортировать workflow в API-format:** в ComfyUI меню → включить dev-режим (Settings → «Enable Dev mode Options») → «Save (API Format)». Сохранить JSON.
4. **Положить этот JSON в репо:** `agent-web/agent_web/services/comfyui_workflows/sdxl.json` (закоммитить). Бэк на маке подставляет в него prompt/seed/steps/cfg. Запомнить имена нод (positive prompt, KSampler, checkpoint) — понадобятся бэку.

---

## ШАГ 8. Метрик-агент (CPU/RAM/GPU/VRAM)

Файл `week-06/metrics_server.py` (создаётся Mac-сессией по основному плану; если ещё нет — пропустить, вернуться позже). Запуск:
```powershell
pip install psutil
python week-06\metrics_server.py
```
- Слушает `0.0.0.0:11435`, отдаёт JSON `{cpu_pct, ram_used, ram_total, gpu_pct, vram_used, vram_total, gpu_temp, ollama_models}`.
- Firewall на 11435 (от админа):
```powershell
New-NetFirewallRule -DisplayName "Metrics 11435" -Direction Inbound -Protocol TCP -LocalPort 11435 -Action Allow
```
Проверка:
```powershell
curl http://localhost:11435/metrics
```

---

## ШАГ 9. VRAM-реальность (честный замер)

Загрузить обе локальные штуки и посмотреть, что реально помещается в 8GB:
```powershell
ollama run qwen3:4b "тест"   # держит модель в VRAM
# ComfyUI запущен и сгенерил картинку (SDXL в VRAM)
nvidia-smi
ollama ps
```
- Записать: влезают ли Qwen3-4B + SDXL одновременно, или идёт своп/выгрузка. **Задокументировать честно** — это данные для дня 29/30. Qwen3-8B + SDXL одновременно — почти наверняка НЕ влезет (только по очереди).

---

## ШАГ 10. Итог — отдать пользователю

Проверить, что три сервиса отвечают по LAN (с самого Windows по LAN-IP, не localhost):
```powershell
curl http://<LAN-IP>:11434/api/tags     # Ollama
curl http://<LAN-IP>:8188/              # ComfyUI (или /system_stats)
curl http://<LAN-IP>:11435/metrics      # метрики
```
Выдать пользователю строки для `agent-web/.env` на маке (подставить реальный LAN-IP):
```
OLLAMA_CHAT_URL=http://<LAN-IP>:11434/v1
COMFYUI_URL=http://<LAN-IP>:8188
METRICS_URL=http://<LAN-IP>:11435/metrics
```
Готово: железо поднято, endpoint'ы доступны, workflow-JSON закоммичен. Дальше — Mac-сессия по основному плану пилит код agent-web.

---

## ШАГ 11 (день 30). Сам `agent-web` — постоянный сервер на этом ПК

**Контекст:** решение юзера (см. переписку в основной сессии) — Windows-ПК станет постоянным
хостом всего приложения (backend + frontend), не только Ollama/ComfyUI. Mac-сессия написала и
живьём проверила весь код (SSE-чат, картинки, настройки, мониторинг, rate-limit, параллельные
запросы) — здесь просто разворачиваем то же самое на Windows.

1. **Склонировать репо** сюда (или обновить, если уже клонирован для шагов 1-10):
   ```powershell
   git clone <URL-репо> C:\GitRepos\AIAdventChallange
   cd C:\GitRepos\AIAdventChallange\agent-web
   ```
2. **Python-окружение** (используй тот же Python, что уже стоит для Ollama-скриптов):
   ```powershell
   python -m venv .venv
   .venv\Scripts\pip install -e .
   .venv\Scripts\pip install -e ..\agent-cli
   ```
3. **`.env`** в `agent-web\.env` — на самой Windows все LAN-сервисы это `localhost`:
   ```
   OLLAMA_CHAT_URL=http://localhost:11434/v1
   COMFYUI_URL=http://localhost:8188
   METRICS_URL=http://localhost:11435/metrics
   PROXYAPI_KEY=<тот же ключ, что в agent-cli/.env на маке — если нужен облачный fallback>
   ```
4. **Прод-сборка фронта** (Node.js нужен на Windows — `winget install OpenJS.NodeJS.LTS` если
   нет):
   ```powershell
   cd frontend
   npm install
   npm run build
   cd ..
   ```
   Собирается в `agent_web\static\` — бэк раздаёт same-origin, никакого отдельного фронт-сервера
   не нужно в проде.
5. **Firewall на порт 8765:**
   ```powershell
   New-NetFirewallRule -DisplayName "AgentWeb 8765" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow
   ```
6. **Запуск:**
   ```powershell
   .venv\Scripts\python __main__.py
   ```
   По умолчанию слушает `0.0.0.0:8765`, без auto-reload (продовые настройки — см.
   `agent-web/__main__.py`, `AGENT_WEB_HOST`/`AGENT_WEB_PORT`/`AGENT_WEB_RELOAD` в env если нужно
   переопределить).
7. **Проверить с телефона** (та же WiFi, не localhost): `http://<LAN-IP>:8765/` — где LAN-IP тот
   же, что уже записан выше для Ollama/ComfyUI.
8. **Честная оговорка, не автозапуск:** как и ComfyUI, это НЕ Windows-сервис — процесс живёт,
   пока открыт терминал (или `pythonw` в фоне вручную). Если после ребута нужен автозапуск —
   `Task Scheduler` (Trigger: At log on, Action: `.venv\Scripts\python.exe __main__.py`,
   Start in: путь к `agent-web`) — не настраивали, не просили; если сделаешь — впиши сюда.
9. **Что уже проверено на маке живьём** (эквивалентно должно работать и здесь): реальный чат
   через Ollama и ProxyAPI, генерация картинки через ComfyUI, панель настроек реально влияет на
   генерацию, HUD мониторинга (офлайн/онлайн), rate-limit (30 запросов/60с на IP), 3 параллельных
   чат-запроса — не падает, ответы не путаются между сессиями, но Ollama сериализует на одной
   GPU (реально ~2с генерации, но ~17-21с wall time при 3 параллельных — это очередь, не
   параллелизм, задокументировано честно в `week-06/day-30/README.md`).

---

## Порты / сервисы (шпаргалка)

| Сервис | Порт | Команда запуска | Проверка |
|--------|------|-----------------|----------|
| Ollama | 11434 | (сервис, `OLLAMA_HOST=0.0.0.0`) | `curl :11434/api/tags` |
| ComfyUI | 8188 | `python main.py --listen 0.0.0.0 --port 8188 --lowvram` | `http://:8188` |
| Метрики | 11435 | `python week-06\metrics_server.py` | `curl :11435/metrics` |
