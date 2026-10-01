# Hyperagent Local File Bridge (МОСТ)

Мост, который даёт **облачному агенту** [Hyperagent](https://hyperagent.com) доступ на чтение и запись к **одной папке** на вашем компьютере. Также он работоспособен в [Arena](https://arena.ai/)

Работает так: агент живёт в облаке и до вашего диска сам не дотянется. Мы поднимаем у вас локальный файловый сервер (MCP), выставляем его в интернет через туннель — и агент получает возможность читать/писать файлы в выделенной папке.

```
Агент в облаке  ──HTTPS──▶  туннель  ──▶  supergateway (localhost:8008)  ──▶  filesystem-сервер (только ваша папка)
```

> ⚠️ **Безопасность в двух словах:** сервер заперт в одной папке и физически не может выйти за её пределы. URL туннеля — это фактически пароль к этой папке: кто знает URL, тот имеет к ней доступ, пока мост запущен. Не публикуйте URL и не открывайте доступ к системным папкам.

> ℹ️ Инструкция проверена на практике (Windows 11 + PowerShell 5.1, Node 20, devtunnel 1.0.2094): все подводные камни, которые реально встречаются, собраны в разделе [Устранение неполадок](#устранение-неполадок) и в [чек-листе](#чек-лист-мост-не-работает).

---

## Что понадобится

- **Windows** (инструкция для него; на macOS/Linux шаги аналогичны).
- **[Node.js](https://nodejs.org) 18+** — проверить: `node -v`.
- Аккаунт **Microsoft или GitHub** — для туннеля (вход обязателен всегда; анонимным может быть только доступ клиентов, но не хостинг).
- **[VS Code](https://code.visualstudio.com)** — **не обязателен**. Нужен только для Способа A.

Создайте выделенную папку, к которой откроете доступ агенту:

```powershell
mkdir C:\hyperagent-bridge
```

> 🔴 Папка должна **существовать до запуска сервера**. Если указать несуществующий путь, файловый сервер упадёт при первом же запросе (агент получит `MCP server process failed`).

Никогда не указывайте здесь весь диск, домашнюю папку или папки с паролями/ключами.

---

## Шаг 1. Запустить локальный сервер (общий для обоих способов)

В окне PowerShell **одной строкой**:

```powershell
npx -y supergateway --stdio "npx -y @modelcontextprotocol/server-filesystem C:\hyperagent-bridge" --port 8008 --outputTransport streamableHttp
```

Должна появиться строка:

```
[supergateway] Listening on port 8008
[supergateway] StreamableHttp endpoint: http://localhost:8008/mcp
```

Это значит, сервер слушает порт 8008. Окно **не закрывайте** — пока оно открыто, сервер живёт.

- `@modelcontextprotocol/server-filesystem` — официальный файловый MCP-сервер (Anthropic), заперт в указанной папке.
- `supergateway` — превращает stdio-сервер в HTTP-сервис (`/mcp`, транспорт Streamable HTTP).

**Проверьте сервер до туннеля** (новое окно PowerShell; не заменяет окно сервера):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-bridge.ps1
```

Скрипт проверит и локальный порт 8008, и внешний адрес (если он уже есть). Успех — сообщение `secure-filesystem-server`. Если у вас ещё нет туннеля — он честно скажет, что локальный сервер в порядке.

<details>
<summary>Если сервер не поднимается: обёртка <code>cmd /c</code></summary>

На части машин Node не может запустить `npx` без оболочки (npx — это `npx.cmd`, а не .exe). Признак — в окне сервера появляется `Child stderr`/`Child exited`, агент получает `MCP server process failed`. Тогда запускайте сервер так:

```powershell
npx -y supergateway --stdio "cmd /c npx -y @modelcontextprotocol/server-filesystem C:\hyperagent-bridge" --port 8008 --outputTransport streamableHttp
```

</details>

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

---

### Способ B — devtunnel CLI + батник (постоянный URL, автозапуск) ⭐

Годится «настроил и забыл»: адрес не меняется, мост поднимается двойным кликом. **VS Code не нужен.**

Ниже — полный путь с проверками на каждом шаге. Всё, что помечено *(один раз)*, делается однократно; остальное — при каждом запуске моста.

#### B.1. Установить CLI *(один раз)*

```powershell
winget install --id Microsoft.devtunnel --accept-source-agreements --accept-package-agreements
```

Установщик скажет `Path environment variable modified; restart your shell to use the new value.` — **текущее окно не увидит команду**, пока не обновить PATH:

```powershell
$env:Path = [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
```

Проверка:

```powershell
devtunnel --version
```

Если `winget` недоступен — скачайте CLI вручную: https://aka.ms/TunnelsCliDownload/win-x64

#### B.2. Войти в аккаунт *(один раз)*

```powershell
devtunnel user login
```

Откроется браузер — войдите учёткой Microsoft (или GitHub) и подтвердите доступ. Это авторизация **владельца туннеля**; агенту она не передаётся и никакой «ключ» ему не нужен.

Если браузер не открылся или вход не проходит — вход по коду устройства:

```powershell
devtunnel user login -d
```

Появится код и ссылка `https://microsoft.com/devicelogin` — откройте с любого устройства (можно с телефона), введите код. Для входа через GitHub: `devtunnel user login -g -d` (код вводится на https://github.com/login/device).

Проверка входа:

```powershell
devtunnel user show
```

Должно быть написано, под каким аккаунтом вы вошли (`Logged in as ... using Microsoft`).

#### B.3. Создать постоянный туннель *(один раз)*

```powershell
devtunnel create -a
```

- Флаг `-a` = `--allow-anonymous`: разрешает подключаться **без логина** по одной лишь ссылке. Без него агент будет получать страницу входа Microsoft / `401`.
- Команда напечатает **Tunnel ID** вида `abcd1234.eun1` — запишите его.
- Туннель живёт 30 дней и продлевается при использовании. Если долго не пользоваться — пересоздать (`devtunnel create -a`).

Привязать порт к туннелю *(один раз)*:

```powershell
devtunnel port create <ВАШ_TUNNEL_ID> -p 8008
```

#### B.4. Запустить сервер и туннель (каждый раз)

Окно 1 — сервер (Шаг 1 выше). Окно 2 — туннель:

```powershell
devtunnel host <ВАШ_TUNNEL_ID> --allow-anonymous
```

Успех выглядит так:

```
Hosting port: 8008
Connect via browser: https://xxxxxxxx-8008.euw.devtunnels.ms
Ready to accept connections for tunnel: <имя-туннеля>
```

**Оба окна должны оставаться открытыми.** Закрыли окно туннеля (`Ctrl+C`) — мост выключен. Итоговый URL для агента = `Connect via browser` + `/mcp`:

```
https://xxxxxxxx-8008.euw.devtunnels.ms/mcp
```

Узнать адрес позже, если окно потерялось:

```powershell
devtunnel show <ВАШ_TUNNEL_ID>
```

> 💡 **Если неохота настраивать постоянный туннель** — есть совсем короткий путь. Одна команда создаёт временный туннель, сама печатает адрес и удаляется при закрытии окна (адрес при каждом запуске новый):
> ```powershell
> devtunnel host -p 8008 --allow-anonymous
> ```

#### B.5. Выключить / убрать совсем

- Выключить мост: закрыть окна сервера и туннеля (`Ctrl+C`).
- Забыли `--allow-anonymous`, а туннель уже создан? Выдать анонимный доступ существующему:
  ```powershell
  devtunnel access create <ВАШ_TUNNEL_ID> --anonymous
  ```
- Удалить постоянный туннель: `devtunnel delete <ВАШ_TUNNEL_ID>` (все сразу — `devtunnel delete-all`).
- Посмотреть список своих туннелей: `devtunnel list`.

---

## Шаг 3. Подключить агента

Способ подключения зависит от платформы:

- **Клиент с поддержкой OAuth-MCP** (форма «Add MCP server») — сработает только если у сервера есть OAuth. У этого простого моста OAuth нет, поэтому такая форма выдаст ошибку `Failed to start MCP OAuth`. Это нормально.
- **Прямой вызов из агента** — агент обращается к `https://<туннель>/mcp` напрямую (JSON-RPC поверх HTTP). Для этого используйте скрипт `scripts/bridge.py` (см. ниже) или встроенные средства вашей платформы.

**Что именно передать агенту:** только адрес `https://<туннель>/mcp`. Никаких токенов, паролей и ключей передавать не нужно (и не следует) — доступ регулируется флагом `--allow-anonymous` / видимостью порта.

> **Пользователям Hyperagent:** в репозитории лежит готовый скилл [`skill-local-pc-file-bridge.json`](./skill-local-pc-file-bridge.json). Импортируйте его (Learning → Skills) или просто пришлите файл своему агенту со словами «поставь этот скилл». После импорта впишите **свой** `BRIDGE_URL` (адрес туннеля + `/mcp`) в credentials скилла — чужой адрес в файле не хранится, там только заглушка.

Проверка вручную (агент делает то же самое):

```bash
curl -s -X POST "https://<туннель>/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
```

Успех — ответ с `"serverInfo":{"name":"secure-filesystem-server"...}`.

> В PowerShell многострочные команды вставлять нельзя — консоль ломает такие вставки (появляется приглашение `>>`). Команды для PowerShell даны **одной строкой**; если случайно попали в `>>` — нажмите `Ctrl+C`.

---

## Батник (start-bridge.bat)

Однокликовый запуск моста. Откройте файл в блокноте и настройте 3 строки вверху:

```bat
set "FOLDER=C:\hyperagent-bridge"      REM какая папка доступна агенту
set "PORT=8008"                         REM порт (менять не нужно)
set "TUNNEL_ID=abcd1234.eun1"          REM ваш Tunnel ID из devtunnel create
```

Двойной клик → откроются два окна: **server** (supergateway) и **tunnel** (devtunnel). Оба должны оставаться открытыми. Закрыть окно = выключить мост.

**Проверка, что батник настроен:** в окне туннеля не должно быть строки `Tunnel not found: PUT-YOUR-TUNNEL-ID-HERE`. Если она есть — вы запустили батник с заглушкой вместо своего `TUNNEL_ID`.

> 🔴 **Не запускайте батник, если сервер уже запущен вручную** в другом окне. Оба займут порт 8008 — сервер из батника упадёт с ошибкой занятого порта (`EADDRINUSE`). Держите только один запущенный сервер.

**Несколько папок или путь с пробелом:** список в `FOLDER` разделяется пробелами, поэтому путь вроде `E:\Games\My Game II` развалится. Оборачивайте **каждый** путь в `\"...\"`:

```bat
set "FOLDER=\"C:\projects\" \"E:\Games\My Game II\" \"D:\docs\""
```

**Автозапуск при входе в Windows:** `Win+R` → `shell:startup` → Enter → положите туда ярлык на `start-bridge.bat`.

---

## Скрипт-клиент (scripts/bridge.py)

CLI для работы с файлами через мост. Адрес моста берётся из переменной окружения `BRIDGE_URL` (адрес туннеля + `/mcp`) либо из флага `--url`:

```bash
export BRIDGE_URL="https://<туннель>/mcp"     # Windows: set BRIDGE_URL=...
python3 scripts/bridge.py probe                # проверка связи: initialize + список инструментов
python3 scripts/bridge.py allowed              # какие папки доступны
python3 scripts/bridge.py ls C:/hyperagent-bridge
python3 scripts/bridge.py read C:/hyperagent-bridge/file.txt
echo "hello" | python3 scripts/bridge.py write C:/hyperagent-bridge/new.txt
```

Работает и без переменной окружения:

```bash
python3 scripts/bridge.py --url https://<туннель>/mcp allowed
```

Команды: `probe`, `tools`, `allowed`, `ls`, `tree`, `read`, `write` (контент из stdin), `mkdir`, `mv`, `search`, `info`, `call`.

Мелочи, которые уже учтены в скрипте: правильная сборка SSE-ответов, **принудительный UTF-8** (иначе русский текст превращается в кракозябры), понятные подсказки при `401/403/404/502`.

**Как узнать, какая папка отдана агенту:** спросите агента (`list_allowed_directories`) или посмотрите строку в окне сервера:

```
[supergateway]   - stdio: npx -y @modelcontextprotocol/server-filesystem <ЭТО И ЕСТЬ ПАПКА>
```

---

## Инструменты файлового сервера

`read_file`, `read_text_file`, `read_media_file`, `read_multiple_files`, `write_file`, `edit_file`, `create_directory`, `list_directory`, `list_directory_with_sizes`, `directory_tree`, `move_file`, `search_files`, `get_file_info`, `list_allowed_directories`.

---

## Устранение неполадок

| Симптом | Причина / решение |
|---|---|
| `'devtunnel' is not recognized` | Программа установилась, но PATH не обновлён — обновите PATH (команда в B.1) или откройте новое окно PowerShell |
| `Tunnel not found: PUT-YOUR-TUNNEL-ID-HERE` | Батник запущен с заглушкой — впишите свой Tunnel ID из `devtunnel create -a` |
| Агент/браузер получает HTML-страницу логина Microsoft или `401/403` | Туннель приватный. Нужен `--allow-anonymous` при `host` (или `devtunnel access create <ID> --anonymous` для уже созданного туннеля). Для Способа A — Port Visibility → Public |
| В ответе агента пусто / timeout, ответа нет совсем | Закрыто окно туннеля или сервера; либо **адрес устарел** (у временного туннеля он меняется при каждом запуске) — поднимите заново и пришлите агенту новый URL |
| `-32603 MCP server process failed` | Упал дочерний файловый сервер. В 9 случаях из 10 — указанной папки не существует. Проверьте `Test-Path <папка>`, создайте её и перезапустите сервер. Точную причину смотрите в окне сервера: строки `Child stderr:` и `Child exited:` |
| В окне сервера: `None of the specified directories are accessible` | Папка не существует или нет прав — создайте папку / проверьте путь |
| `spawn npx ENOENT` / сервер падает сразу | Node на Windows не запускает `npx.cmd` напрямую — используйте обёртку `cmd /c` (см. свёртку в Шаге 1) |
| 404 на `/mcp` | supergateway запущен в SSE-режиме — добавьте `--outputTransport streamableHttp` |
| Порт 8008 занят, сервер падает с `EADDRINUSE` | Запущены два сервера (например, батник и ручной запуск) — оставьте один |
| Проверить, что порт вообще слушается | `Get-NetTCPConnection -LocalPort 8008 -State Listen` — если пусто, сервер не работает |
| `Failed to start MCP OAuth` (форма «Add MCP server») | Ожидаемо: у моста нет OAuth. Используйте прямой вызов через `/mcp` |
| Браузер показывает страницу «вы собираетесь перейти…» (антифишинг Microsoft) | Это только для браузерного открытия ссылки; агент делает POST JSON-RPC и проходит мимо неё |
| Кракозябры в окне батника | Косметика (кодировка консоли), на работу не влияет |
| Русский текст в файлах читается как `ÐŸÑ€Ð¸Ð²ÐµÑ‚` | Это баг **клиента** (декодирование Latin-1 вместо UTF-8), не моста. В `scripts/bridge.py` уже исправлено; в своём коде явно декодируйте ответы как UTF-8 |
| Папка с пробелом в пути не попала в доступные | Список папок разбивается по пробелам. Оборачивайте каждый путь в `\"...\"` внутри `FOLDER` — пример есть в `start-bridge.bat`. Проверка: спросите агента, какие папки ему доступны |
| Туннель перестал работать через месяц | Туннели devtunnel живут 30 дней; продлеваются при использовании. Пересоздайте: `devtunnel create -a` → `devtunnel port create <новый_ID> -p 8008` |

### Чек-лист «мост не работает»

Проверяйте строго по порядку — это отсекает 90% случаев:

1. **Окно сервера открыто?** Есть строка `Listening on port 8008`? Нет ошибок `Child exited`?
2. **Порт слушается?** `Get-NetTCPConnection -LocalPort 8008 -State Listen`
3. **Сервер отвечает локально?** `powershell -ExecutionPolicy Bypass -File .\scripts\check-bridge.ps1`
   - Ошибка уже здесь → туннель не виноват, чините сервер (папка!).
4. **Окно туннеля открыто?** Есть `Hosting port: 8008`?
5. **Адрес актуален?** У временного туннеля он меняется при каждом запуске — сверьте `Connect via browser`.
6. **Ответ через туннель.** Тот же скрипт: `.\scripts\check-bridge.ps1 https://<туннель>`
   - `401`/страница логина → забыт `--allow-anonymous`.
   - `404` → не тот транспорт (`--outputTransport streamableHttp`).
   - Пусто/таймаут → окно туннеля закрыто или адрес устарел.

---

## Компоненты (всё — публичный/официальный код)

- [supergateway](https://github.com/supercorp-ai/supergateway) — stdio↔HTTP шлюз для MCP.
- [@modelcontextprotocol/server-filesystem](https://github.com/modelcontextprotocol/servers) — эталонный файловый MCP-сервер.
- [Microsoft Dev Tunnels](https://learn.microsoft.com/azure/developer/dev-tunnels/) — туннель (тот же, что во вкладке PORTS в VS Code).

---

## Проверка у агента (со стороны облака)

Агент делает ровно это:

1. `initialize` → ожидает `serverInfo.name = secure-filesystem-server`;
2. `tools/list` → ожидает 14 инструментов;
3. `list_allowed_directories` → ожидает путь к вашей папке.

Если все три пункта прошли — мост рабочий, а список папок в третьем пункте и есть ответ на вопрос «какую папку видит агент».
