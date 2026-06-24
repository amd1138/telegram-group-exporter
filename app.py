# -*- coding: utf-8 -*-
"""
Локальный веб-выгружатель сообщений Telegram из группы (от лица своего аккаунта).
Запускается через run.bat — открывается страничка в браузере, всё вводится там.
"""
import os
import json
from datetime import datetime, timezone

import telethon.sync  # делает методы Telethon синхронными (удобно для Flask)
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from flask import Flask, request, jsonify, send_file, Response

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(BASE, "exports")
SESSION = os.path.join(BASE, "account")  # account.session создастся тут
os.makedirs(EXPORT_DIR, exist_ok=True)

app = Flask(__name__)

# Состояние одной сессии (приложение локальное, один пользователь)
client = None
state = {"phone": None}


@app.route("/")
def index():
    with open(os.path.join(BASE, "index.html"), encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")


@app.route("/connect", methods=["POST"])
def connect():
    """Шаг 1: подключение и запрос кода."""
    global client, state
    d = request.get_json(force=True)
    try:
        api_id = int(str(d["api_id"]).strip())
    except (ValueError, KeyError):
        return jsonify({"error": "API_ID должен быть числом"}), 400
    api_hash = str(d.get("api_hash", "")).strip()
    phone = str(d.get("phone", "")).strip()
    if not api_hash or not phone:
        return jsonify({"error": "Заполните api_hash и телефон"}), 400

    client = TelegramClient(SESSION, api_id, api_hash)
    client.connect()
    if client.is_user_authorized():
        return jsonify({"step": "ready", "msg": "Уже авторизованы — можно выгружать."})

    client.send_code_request(phone)
    state["phone"] = phone
    return jsonify({"step": "code", "msg": "Код отправлен в Telegram. Введите его."})


@app.route("/code", methods=["POST"])
def code():
    """Шаг 2: ввод кода из Telegram."""
    d = request.get_json(force=True)
    c = str(d.get("code", "")).strip()
    if client is None:
        return jsonify({"error": "Сначала подключитесь"}), 400
    try:
        client.sign_in(state["phone"], c)
    except SessionPasswordNeededError:
        return jsonify({"step": "password", "msg": "Включён облачный пароль (2FA). Введите его."})
    except Exception as e:
        return jsonify({"error": f"Неверный код: {e}"}), 400
    return jsonify({"step": "ready", "msg": "Готово — авторизованы."})


@app.route("/password", methods=["POST"])
def password():
    """Шаг 2б: облачный пароль (если включён 2FA)."""
    d = request.get_json(force=True)
    try:
        client.sign_in(password=str(d.get("password", "")))
    except Exception as e:
        return jsonify({"error": f"Неверный пароль: {e}"}), 400
    return jsonify({"step": "ready", "msg": "Готово — авторизованы."})


@app.route("/export", methods=["POST"])
def export():
    """Шаг 3: выгрузка всех сообщений группы."""
    d = request.get_json(force=True)
    group = str(d.get("group", "")).strip()
    if not group:
        return jsonify({"error": "Укажите группу"}), 400
    if client is None or not client.is_user_authorized():
        return jsonify({"error": "Сначала авторизуйтесь"}), 400

    limit = d.get("limit")
    try:
        limit = int(limit) if str(limit).strip() else None
    except ValueError:
        limit = None

    with_media = bool(d.get("media"))

    # числовой id (например -1001234567890) -> int
    g = group
    if g.lstrip("-").isdigit():
        g = int(g)

    try:
        entity = client.get_entity(g)
    except Exception as e:
        return jsonify({"error": f"Не удалось открыть группу: {e}. "
                                 "Аккаунт должен состоять в ней."}), 400

    title = getattr(entity, "title", str(group))
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(title))[:50] or "group"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    media_dir = None
    media_count = 0
    if with_media:
        media_dir = os.path.join(EXPORT_DIR, f"media_{safe}_{stamp}")
        os.makedirs(media_dir, exist_ok=True)

    messages = []
    for msg in client.iter_messages(entity, limit=limit, reverse=True):
        sender = msg.sender
        author_name = None
        if sender is not None:
            parts = [getattr(sender, "first_name", None),
                     getattr(sender, "last_name", None)]
            author_name = (" ".join(p for p in parts if p)
                           or getattr(sender, "username", None)
                           or getattr(sender, "title", None))

        media_file = None
        if with_media and msg.media is not None:
            try:
                # имя файла начинается с id сообщения, чтобы не было коллизий
                saved = client.download_media(msg, file=os.path.join(media_dir, str(msg.id)))
                if saved:
                    media_file = os.path.relpath(saved, EXPORT_DIR).replace("\\", "/")
                    media_count += 1
            except Exception as e:
                media_file = f"[ошибка загрузки: {e}]"

        messages.append({
            "id": msg.id,
            "date": msg.date.astimezone(timezone.utc).isoformat() if msg.date else None,
            "author_id": int(msg.sender_id) if msg.sender_id else None,
            "author": author_name,
            "text": msg.message or "",
            "reply_to": int(msg.reply_to_msg_id) if msg.reply_to_msg_id else None,
            "media": media_file,
        })

    json_name = f"export_{safe}_{stamp}.json"
    txt_name = f"export_{safe}_{stamp}.txt"

    with open(os.path.join(EXPORT_DIR, json_name), "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    with open(os.path.join(EXPORT_DIR, txt_name), "w", encoding="utf-8") as f:
        f.write(f"# {title} — {len(messages)} сообщений\n\n")
        for m in messages:
            who = m["author"] or m["author_id"] or "—"
            f.write(f"[{m['date']}] {who}:\n")
            if m["text"]:
                f.write(f"{m['text']}\n")
            if m["media"]:
                f.write(f"[медиа: {m['media']}]\n")
            f.write("\n")

    return jsonify({
        "count": len(messages),
        "title": title,
        "json": json_name,
        "txt": txt_name,
        "media_count": media_count,
        "media_dir": os.path.basename(media_dir) if media_dir else None,
    })


@app.route("/download/<path:name>")
def download(name):
    path = os.path.join(EXPORT_DIR, os.path.basename(name))
    if not os.path.exists(path):
        return "Файл не найден", 404
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    print("\n  Открой в браузере:  http://127.0.0.1:5000\n")
    # threaded=False — чтобы Telethon-сессия жила между запросами
    try:
        app.run(host="127.0.0.1", port=5000, threaded=False, use_reloader=False)
    except OSError as e:
        print("\n[!] Не удалось запустить сервер на порту 5000.")
        print(f"    {e}")
        print("    Скорее всего порт 5000 уже занят другой программой.")
        print("    Закрой её (или перезагрузи компьютер) и запусти run.bat снова.\n")
