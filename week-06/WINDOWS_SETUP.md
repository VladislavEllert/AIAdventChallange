# WINDOWS_SETUP.md — Runbook для Windows-сессии (RTX 4060, 8GB)

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

## Порты / сервисы (шпаргалка)

| Сервис | Порт | Команда запуска | Проверка |
|--------|------|-----------------|----------|
| Ollama | 11434 | (сервис, `OLLAMA_HOST=0.0.0.0`) | `curl :11434/api/tags` |
| ComfyUI | 8188 | `python main.py --listen 0.0.0.0 --port 8188 --lowvram` | `http://:8188` |
| Метрики | 11435 | `python week-06\metrics_server.py` | `curl :11435/metrics` |
