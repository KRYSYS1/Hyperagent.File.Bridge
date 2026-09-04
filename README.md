# Hyperagent Local File Bridge (МОСТ)

Мост, который даёт **облачному агенту** [Hyperagent](https://hyperagent.com) доступ на чтение и запись к **одной папке** на вашем компьютере. Также он работоспособен в [Arena](https://arena.ai/)

Работает так: агент живёт в облаке и до вашего диска сам не дотянется. Мы поднимаем у вас локальный файловый сервер (MCP), выставляем его в интернет через туннель — и агент получает возможность читать/писать файлы в выделенной папке.

```
Агент в облаке  ──HTTPS──▶  туннель  ──▶  supergateway (localhost:8008)  ──▶  filesystem-сервер (только ваша папка)
```

> ⚠️ **Безопасность в двух словах:** сервер заперт в одной папке и физически не может выйти за её пределы. URL туннеля — это фактически пароль к этой папке: кто знает URL, тот имеет к ней доступ, пока мост запущен. Не публикуйте URL и не открывайте доступ к системным папкам.

---

## Что понадобится

- **Windows** (инструкция для него; на macOS/Linux шаги аналогичны).
- **[Node.js](https://nodejs.org) 18+** — проверить: `node -v`.
- **[VS Code](https://code.visualstudio.com)** — для простого способа подключения (Способ A).
- Аккаунт **Microsoft или GitHub** — для туннеля.

Создайте выделенную папку, к которой откроете доступ агенту:

```powershell
mkdir C:\hyperagent-bridge
```

Никогда не указывайте здесь весь диск, домашнюю папку или папки с паролями/ключами.

---

## Шаг 1. Запустить локальный сервер (общий для обоих способов)

В окне PowerShell **одной строкой**:

```powershell
npx -y supergateway --stdio "npx -y @modelcontextprotocol/server-filesystem C:\hyperagent-bridge" --port 8008 --outputTransport streamableHttp
```

Должна появиться строка:

```
StreamableHttp endpoint: http://localhost:8008/mcp
```

Это значит, сервер слушает порт 8008. Окно **не закрывайте** — пока оно открыто, сервер живёт.

- `@modelcontextprotocol/server-filesystem` — официальный файловый MCP-сервер (Anthropic), заперт в указанной папке.
- `supergateway` — превращает stdio-сервер в HTTP-сервис (`/mcp`, транспорт Streamable HTTP).

---

## Шаг 2. Выставить сервер в интернет (два способа)

### Способ A — VS Code Port Forwarding (просто, мышкой)

Годится для разовой работы. URL может меняться между сессиями.

1. Откройте VS Code → нижняя панель → вкладка **PORTS** (если её нет: `Ctrl+Shift+P` → «Ports: Focus on Ports View»).
2. **Forward a Port** → введите `8008`.
3. Войдите через **GitHub / Microsoft**, когда попросит.
4. **Обязательно:** правый клик по строке порта → **Port Visibility → Public** (иначе туннель отдаёт страницу логина вместо данных).
5. Скопируйте адрес вида `https://xxxxx-8008.euw.devtunnels.ms`.

Итоговый URL для агента = этот адрес + `/mcp`:
```
https://xxxxx-8008.euw.devtunnels.ms/mcp
```

### Способ B — devtunnel CLI + батник (постоянный URL, автозапуск)

Годится «настроил и забыл»: постоянный адрес и автостарт при входе в Windows.

Разовая настройка постоянного туннеля:

```powershell
winget install Microsoft.devtunnel
# перезапустите окно PowerShell, чтобы команда devtunnel стала доступна
devtunnel user login
devtunnel create -a
# запомните напечатанный Tunnel ID, вида abcd1234.eun1
devtunnel port create <ВАШ_TUNNEL_ID> -p 8008
```

Дальше используйте `start-bridge.bat` (лежит в этом репозитории): впишите в него свой `TUNNEL_ID`, и он поднимет **и сервер, и туннель** двумя окнами. См. раздел «Батник» ниже.

Итоговый URL для агента печатается в окне туннеля (`Connect via browser: https://...`) + `/mcp`.

> Туннель devtunnel живёт 30 дней и продлевается при использовании. Если долго не пользоваться — пересоздать командой `devtunnel create -a`.

---

## Шаг 3. Подключить агента

Способ подключения зависит от платформы:

- **Клиент с поддержкой OAuth-MCP** (форма «Add MCP server») — сработает только если у сервера есть OAuth. У этого простого моста OAuth нет, поэтому такая форма выдаст ошибку `Failed to start MCP OAuth`. Это нормально.
- **Прямой вызов из агента** — агент обращается к `https://<туннель>/mcp` напрямую (JSON-RPC поверх HTTP). Для этого используйте скрипт `scripts/bridge.py` (см. ниже) или встроенные средства вашей платформы.

> **Пользователям Hyperagent:** в репозитории лежит готовый скилл [`skill-local-pc-file-bridge.json`](./skill-local-pc-file-bridge.json). Импортируйте его (Learning → Skills) или просто пришлите файл своему агенту со словами «поставь этот скилл». После импорта впишите **свой** `BRIDGE_URL` (адрес туннеля + `/mcp`) в credentials скилла — чужой адрес в файле не хранится, там только заглушка.

Проверка вручную (агент делает то же самое):

```bash
curl -s -X POST "https://<туннель>/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
```

Успех — ответ с `"serverInfo":{"name":"secure-filesystem-server"...}`.

---

## Батник (start-bridge.bat)

Однокликовый запуск моста. Откройте файл в блокноте и настройте 3 строки вверху:

```bat
set "FOLDER=C:\hyperagent-bridge"      REM какая папка доступна агенту
set "PORT=8008"                         REM порт (менять не нужно)
set "TUNNEL_ID=abcd1234.eun1"          REM ваш Tunnel ID из devtunnel create
```

Двойной клик → откроются два окна: **server** (supergateway) и **tunnel** (devtunnel). Оба должны оставаться открытыми. Закрыть окно = выключить мост.

**Несколько папок или путь с пробелом:** список в `FOLDER` разделяется пробелами, поэтому путь вроде `E:\Games\My Game II` развалится. Оборачивайте **каждый** путь в `\"...\"`:

```bat
set "FOLDER=\"C:\projects\" \"E:\Games\My Game II\" \"D:\docs\""
```

**Автозапуск при входе в Windows:** `Win+R` → `shell:startup` → Enter → положите туда ярлык на `start-bridge.bat`.

---

## Скрипт-клиент (scripts/bridge.py)

CLI для работы с файлами через мост. Адрес моста берётся из переменной окружения `BRIDGE_URL` (адрес туннеля + `/mcp`).

```bash
export BRIDGE_URL="https://<туннель>/mcp"     # Windows: set BRIDGE_URL=...
python3 scripts/bridge.py allowed              # какие папки доступны
python3 scripts/bridge.py ls C:/hyperagent-bridge
python3 scripts/bridge.py read C:/hyperagent-bridge/file.txt
echo "hello" | python3 scripts/bridge.py write C:/hyperagent-bridge/new.txt
```

Команды: `tools`, `allowed`, `ls`, `tree`, `read`, `write` (контент из stdin), `mkdir`, `mv`, `search`, `info`, `call`.

---

## Инструменты файлового сервера

`read_file`, `read_text_file`, `read_media_file`, `read_multiple_files`, `write_file`, `edit_file`, `create_directory`, `list_directory`, `list_directory_with_sizes`, `directory_tree`, `move_file`, `search_files`, `get_file_info`, `list_allowed_directories`.

---

## Устранение неполадок

| Симптом | Причина / решение |
|---|---|
| `'cloudflared'/'devtunnel' is not recognized` | Программа установилась, но PATH не обновлён — перезапустите окно PowerShell |
| Cloudflare-туннель падает на порт 7844 | Сеть блокирует порт 7844 — используйте VS Code / devtunnel (работают через 443) |
| В ответе HTML-страница логина | Visibility порта не Public (Способ A) или туннель без `--allow-anonymous` (Способ B) |
| 404 на `/mcp` | supergateway запущен в SSE-режиме — добавьте `--outputTransport streamableHttp` |
| Ответы падают / timeout | Не запущен сервер или туннель — проверьте, что оба окна открыты |
| Форма OAuth: `Failed to start MCP OAuth` | Ожидаемо: у моста нет OAuth. Используйте прямой вызов через `/mcp` |
| Кракозябры в окне батника | Косметика (кодировка консоли), на работу не влияет |
| Папка с пробелом в пути не попала в доступные | Список папок разбивается по пробелам. Оборачивайте каждый путь в `\"...\"` внутри `FOLDER` — пример есть в `start-bridge.bat`. Проверка: спросите агента, какие папки ему доступны |

---

## Компоненты (всё — публичный/официальный код)

- [supergateway](https://github.com/supercorp-ai/supergateway) — stdio↔HTTP шлюз для MCP.
- [@modelcontextprotocol/server-filesystem](https://github.com/modelcontextprotocol/servers) — эталонный файловый MCP-сервер.
- [Microsoft Dev Tunnels](https://learn.microsoft.com/azure/developer/dev-tunnels/) — туннель (тот же, что во вкладке PORTS в VS Code).
