from telethon import TelegramClient, events
from dotenv import load_dotenv
import os
from openai import OpenAI
import json

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TARGET_CHAT = os.getenv("TARGET_CHAT")
MY_TELEGRAM_ID = int(os.getenv("MY_TELEGRAM_ID"))

openai_client = OpenAI(api_key=OPENAI_API_KEY)
client = TelegramClient('guardian_session', API_ID, API_HASH)


async def process_message(event):
    text = event.text or ""
    print(f"[MSG] {text}")

    if len(text.strip()) < 10 or len(text.strip()) > 300:
        return  # слишком короткие и слишком длинные — пропускаем

    prompt = (
        f"Ты — помощник, который извлекает адреса из сообщений в Telegram о происшествиях в Одессе.\n\n"
        f"Сообщение: {text}\n\n"
        f"Твоя задача:\n"
        f"- Нужны только те сообщения, которые касаются только этих районов Одессы:\n"
        f"  • Киевский район (Таирова)\n"
        f"  • Хаджибейский район (Варненская, Гайдара, Филатова и пр.)\n"
        f"  • Большой Фонтан\n"
        f"  • Черноморка\n"
        f"  • Лиманка\n\n"
        f"Список улиц, которые могут быть (не полный список старых названий):\n"
        f"Ильфа и Петрова, Вильямса, Королева, Архитекторская, Маршала Жукова, Люстдорфская дорога, Левитана, Костанди, Глушко, Тополевая, Вузовский, Шишкина, Львовская, Гайдара, Филатова, Варненская, Якира, Космонавтов, Комарова, 25 чапаевской и др. \n\n"
        f"- Учитывай, что в сообщении могут использоваться:\n"
        f"  • старые названия улиц,\n"
        f"  • орфографические или фонетические ошибки,\n"
        f"  • сленговые или сокращённые формы.\n\n"
        f"- Используй контекст и ориентиры для определения адреса. Тщательно проверяй названия улиц.\n"
        f"- Если место соответствует указанным районам — `match: true`, иначе — `match: false`.\n"
        f"- Укажи полный адрес (с новым и старым названием улицы, если известно), номер дома (если указан) и ориентир (если упомянут).\n"
        f"- Также выдели краткую суть происходящего (в 2–5 словах).\n"
        f"- Ответ строго в формате JSON. Никакого текста вне JSON.\n\n"
        f"Пример:\n"
        f'''{{
  "match": true,
  "address": "ул. Академика Глушко (новое: ул. Ярослава Мудрого), дом 22, ориентир: ТЦ Пальмира Плаза",
  "summary": "пакуют мужика"
}}'''
    )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.choices[0].message.content
        print(f"[RAW GPT] {raw}")

        if raw.startswith("```"):
            raw = raw.strip("`").strip("json").strip()

        data = json.loads(raw)

        if data.get("match") and data.get("address"):
            await client.send_message(MY_TELEGRAM_ID, f"{data['address']}\n {data['summary']}")
            print("🟢 Сработал")
    except Exception as e:
        print(f"[ERROR] {e}")


@client.on(events.NewMessage(chats=TARGET_CHAT))
async def handler(event):
    await process_message(event)


async def main():
    print("🔁 Обрабатываю последние 10 сообщений...")
    async for msg in client.iter_messages(TARGET_CHAT, limit=5, reverse=False):
        await process_message(msg)
        print("🟢 Сработал")

    print("🟢 Внимательно слушаю...")
    await client.run_until_disconnected()


client.start()
print("🟢 Saver started and listening...")
client.loop.run_until_complete(main())
