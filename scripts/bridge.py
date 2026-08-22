#!/usr/bin/env python3
"""МОСТ: доступ к файлам на компьютере пользователя через MCP-туннель.

Требуется env-переменная BRIDGE_URL (адрес туннеля + /mcp) — запускать через
RunWithCredentials, credentials скилла подставятся автоматически.

Команды:
  python3 bridge.py tools                     # список инструментов сервера
  python3 bridge.py allowed                   # разрешённые папки
  python3 bridge.py ls <path>                 # содержимое папки
  python3 bridge.py tree <path>               # дерево папки (JSON)
  python3 bridge.py read <path>               # прочитать текстовый файл
  cat local.txt | python3 bridge.py write <path>   # записать файл (контент из stdin)
  python3 bridge.py mkdir <path>              # создать папку
  python3 bridge.py mv <src> <dst>            # переместить/переименовать
  python3 bridge.py search <path> <pattern>   # поиск файлов по имени
  python3 bridge.py info <path>               # метаданные файла
  python3 bridge.py call <tool> '<json>'      # любой инструмент напрямую

Пути указывать в формате C:/hyperagent-bridge/... (прямые слэши работают в Windows).
"""
import json
import os
import sys

import requests

URL = os.environ.get("BRIDGE_URL", "").strip()


def rpc(method, params=None, rid=1):
    if not URL:
        sys.exit("Ошибка: env BRIDGE_URL не задан. Запускайте через RunWithCredentials.")
    r = requests.post(
        URL,
        json={"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}},
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        timeout=90,
    )
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if "text/event-stream" in ctype:
        # SSE: одно событие может содержать несколько строк data: (большие файлы
        # сервер дробит). Склеиваем строки по событиям и берём именно JSON-RPC
        # ответ, пропуская серверные запросы вроде roots/list.
        events, cur = [], []
        for line in r.text.split("\n"):
            line = line.rstrip("\r")
            if line == "":
                if cur:
                    events.append("\n".join(cur))
                    cur = []
            elif line.startswith("data:"):
                cur.append(line[len("data:"):].lstrip())
        if cur:
            events.append("\n".join(cur))
        for ev in events:
            try:
                msg = json.loads(ev)
            except json.JSONDecodeError:
                continue
            if isinstance(msg, dict) and ("result" in msg or "error" in msg):
                return msg
        raise RuntimeError("SSE без JSON-RPC ответа: " + r.text[:300])
    return r.json()


def call_tool(name, args):
    res = rpc("tools/call", {"name": name, "arguments": args})
    if "error" in res:
        raise RuntimeError("MCP error: " + json.dumps(res["error"], ensure_ascii=False))
    content = res.get("result", {}).get("content", [])
    return "\n".join(c.get("text", "") for c in content if c.get("type") == "text")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "tools":
        res = rpc("tools/list")
        for t in res["result"]["tools"]:
            print(t["name"], "—", (t.get("description") or "")[:100])
    elif cmd == "allowed":
        print(call_tool("list_allowed_directories", {}))
    elif cmd == "ls":
        print(call_tool("list_directory", {"path": sys.argv[2]}))
    elif cmd == "tree":
        print(call_tool("directory_tree", {"path": sys.argv[2]}))
    elif cmd == "read":
        print(call_tool("read_text_file", {"path": sys.argv[2]}))
    elif cmd == "write":
        content = sys.stdin.read()
        print(call_tool("write_file", {"path": sys.argv[2], "content": content}))
    elif cmd == "mkdir":
        print(call_tool("create_directory", {"path": sys.argv[2]}))
    elif cmd == "mv":
        print(call_tool("move_file", {"source": sys.argv[2], "destination": sys.argv[3]}))
    elif cmd == "search":
        print(call_tool("search_files", {"path": sys.argv[2], "pattern": sys.argv[3]}))
    elif cmd == "info":
        print(call_tool("get_file_info", {"path": sys.argv[2]}))
    elif cmd == "call":
        print(call_tool(sys.argv[2], json.loads(sys.argv[3])))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
