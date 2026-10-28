#& C:\Users\2105f\AppData\Local\Python\pythoncore-3.14-64\python.exe c:/Users/2105f/bot2.py

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command, Filter
from aiogram.enums import ParseMode, ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import asyncio
import sys
import os
import random


#переменные
TOKEN = "8958441407:AAFZdgoKkyvDmk35vZ7gXnICyZ_OuGXjFQw"
GROUP_ID = -1003005008797 
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

#важное
games = {}

#списки
LOCATIONS = [
    "Аэропорт", "Больница", "Школа", "Пляж", "Космодром",
    "Ресторан", "Кинотеатр", "Поезд", "Офис", "Зоопарк",
    "Музей", "Стадион", "Отель", "Банк", "Парк"
]


#классы
class GameStates(StatesGroup):
    lobby = State()
    playing = State()
    voting = State()



#команды
def lobby_keyboard(players_count: int):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Присоединиться ({players_count})", callback_data="join")
    builder.button(text="Начать игру", callback_data="start_game")
    builder.button(text="Отменить", callback_data="cancel_game")
    builder.adjust(1)
    return builder.as_markup()

def vote_keyboard(players: list):
    builder = InlineKeyboardBuilder()
    for user_id, name in players:
        builder.button(text=name, callback_data=f"vote:{user_id}")
    builder.adjust(2)
    return builder.as_markup()



#главный код

@router.message(Command("newgame"))
async def new_game(message: Message, state: FSMContext):
    print(f"Получена команда /newgame от {message.from_user.id} в чате {message.chat.id}")
    
    if message.chat.type == "private":
        await message.answer("Играть можно только в группе!")
        return
    
    chat_id = message.chat.id
    if chat_id in games:
        await message.answer("Игра уже создана!")
        return

    games[chat_id] = {
        "host": message.from_user.id,
        "players": {message.from_user.id: message.from_user.full_name},
        "status": "lobby"
    }

    await message.answer(
        f"Игра «Шпион» создана!\nИгроков: 1\n\nЖми кнопку, чтобы присоединиться.",
        reply_markup=lobby_keyboard(1)
    )
    await state.set_state(GameStates.lobby)

@router.callback_query(F.data == "join")
async def join_game(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user

    if chat_id not in games:
        await callback.answer("Игра не найдена", show_alert=True)
        return

    game = games[chat_id]
    if game["status"] != "lobby":
        await callback.answer("Игра уже началась!", show_alert=True)
        return

    if user.id in game["players"]:
        await callback.answer("Ты уже в игре!")
        return

    game["players"][user.id] = user.full_name
    count = len(game["players"])

    await callback.message.edit_text(
        f"Игра «Шпион»\nИгроков: {count}\n\nЖми кнопку, чтобы присоединиться.",
        reply_markup=lobby_keyboard(count)
    )
    await callback.answer("Ты в игре!")

@router.callback_query(F.data == "start_game")
async def start_game(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game["host"] != callback.from_user.id:
        await callback.answer("Только хост может начать!", show_alert=True)
        return

    players = list(game["players"].items())
    if len(players) < 1:
        await callback.answer("Нужно минимум 3 игрока!", show_alert=True)
        return

    # Выбираем шпиона и локацию
    spy_id = random.choice([p[0] for p in players])
    location = random.choice(LOCATIONS)

    game["status"] = "playing"
    game["spy"] = spy_id
    game["location"] = location
    game["votes"] = {}

    # Раздаём роли в личку
    for user_id, name in players:
        try:
            if user_id == spy_id:
                await bot.send_message(
                    user_id,
                    "🕵️ <b>Ты — ШПИОН!</b>\nЛокацию ты не знаешь.\n\n"
                    "Чтобы угадать локацию, напиши в группу:\n"
                    "<code>/guess Название локации</code>",
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    user_id,
                    f"📍 <b>Локация:</b> {location}\nТы обычный игрок.",
                    parse_mode="HTML"
                )
        except Exception:
            await callback.message.answer(
                f"Не смог написать {name} в личку. Пусть сначала напишет боту /start"
            )

    # Порядок хода (случайный)
    order = players.copy()
    random.shuffle(order)

    order_text = "🗣 <b>Порядок высказываний:</b>\n\n"
    for i, (user_id, name) in enumerate(order, 1):
        order_text += f"{i}. {name}\n"

    await callback.message.edit_text(
        f"Игра началась! Игроков: {len(players)}\n\n"
        f"{order_text}\n"
        f"Обсуждайте. Когда будете готовы — напишите /vote\n\n"
        f"Шпион может угадать локацию командой:\n"
        f"<code>/guess Название</code>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(Command("guess"))
async def guess_location(message: Message, bot: Bot):
    chat_id = message.chat.id
    game = games.get(chat_id)

    if not game or game["status"] != "playing":
        return

    # Проверяем, что пишет именно шпион
    if message.from_user.id != game["spy"]:
        await message.reply("Только шпион может угадывать локацию!")
        return

    # Берём текст после команды
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Напиши так: /guess Название локации")
        return

    guess = args[1].strip().lower()
    real_location = game["location"].lower()

    spy_name = game["players"][game["spy"]]

    if guess == real_location:
        text = (
            f"🕵️ <b>Шпион угадал локацию!</b>\n\n"
            f"Шпион: {spy_name}\n"
            f"Локация: {game['location']}\n\n"
            f"Победа шпиона!"
        )
    else:
        text = (
            f"❌ Шпион не угадал!\n\n"
            f"Шпион: {spy_name}\n"
            f"Правильная локация: {game['location']}\n\n"
            f"Победа мирных!"
        )

    await message.answer(text, parse_mode="HTML")
    del games[chat_id]

@router.message(Command("vote"))
async def start_voting(message: Message):
    chat_id = message.chat.id
    game = games.get(chat_id)

    if not game or game["status"] != "playing":
        return

    game["status"] = "voting"
    players = list(game["players"].items())

    await message.answer(
        "Голосование! Выберите, кто шпион:",
        reply_markup=vote_keyboard(players)
    )

@router.callback_query(F.data.startswith("vote:"))
async def process_vote(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)
    if not game or game["status"] != "voting":
        return

    voter_id = callback.from_user.id
    voted_id = int(callback.data.split(":")[1])

    if voter_id not in game["players"]:
        await callback.answer("Ты не в игре!")
        return

    game["votes"][voter_id] = voted_id
    await callback.answer("Голос принят!")

    # Когда все проголосовали
    if len(game["votes"]) == len(game["players"]):
        # Подсчёт
        from collections import Counter
        results = Counter(game["votes"].values())
        most_voted = results.most_common(1)[0][0]

        spy_id = game["spy"]
        location = game["location"]
        spy_name = game["players"][spy_id]

        if most_voted == spy_id:
            text = f"🎉 Шпиона поймали!\nШпион был: {spy_name}\nЛокация: {location}"
        else:
            text = f"🕵️ Шпион победил!\nШпион был: {spy_name}\nЛокация: {location}"

        await callback.message.edit_text(text)
        del games[chat_id]














async def terminal_listener():
    await asyncio.sleep(1)
    print("\n💬 Теперь вы можете писать сообщения в терминал!")
    print("👉 Чтобы отправить в ГРУППУ: просто введите текст.")
    print("👉 Чтобы отправить ПОЛЬЗОВАТЕЛЮ: введите ID:текст (например, 1876083446:Привет)\n")
    
    while True:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, sys.stdin.readline)
        text = text.strip()
        
        if text:
            if ":" in text:
                try:
                    target_id, message_text = text.split(":", 1)
                    target_id = int(target_id.strip())
                    message_text = message_text.strip()
                    
                    await bot.send_message(chat_id=target_id, text=message_text)
                    print(f"👤 ЛС для [{target_id}] отправлено: {message_text}")
                except ValueError:
                    try:
                        await bot.send_message(chat_id=GROUP_ID, text=text)
                        print(f"✅ Отправлено в группу: {text}")
                    except Exception as e:
                        print(f"❌ Ошибка отправки в группу: {e}")
                except Exception as e:
                    print(f"❌ Не удалось отправить пользователю {target_id}: {e}")
                    print("⚠️ Убедитесь, что ID правильный и пользователь запустил бота!")
            else:
                try:
                    await bot.send_message(chat_id=GROUP_ID, text=text)
                    print(f"✅ Отправлено в группу: {text}")
                except Exception as e:
                    print(f"❌ Ошибка: {e}")

async def main():
    print("Бот запускается...")
    dp.include_router(router)
    await asyncio.gather(
        dp.start_polling(bot, skip_updates=True),
        terminal_listener()  # если используешь
    )

if __name__ == "__main__":
    asyncio.run(main())
