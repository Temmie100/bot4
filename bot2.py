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
from threading import Thread
from flask import Flask
import time
from aiogram.filters import CommandObject
from aiogram.fsm.storage.base import StorageKey



# 1. Настройка Flask для Render (чтобы хостинг не отключал бота)
app = Flask('')

@app.route('/')
def home():
    return "Бот запущен и работает!"

def run_flask():
    # Render автоматически передает нужный порт в переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)







#переменные
TOKEN = "8958441407:AAFZdgoKkyvDmk35vZ7gXnICyZ_OuGXjFQw"
GROUP_ID = -1003005008797 
ADMIN_ID = 1876083446
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()


#важное
games = {}
crypto_balances = {}

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

class TrueFalseStates(StatesGroup):
    waiting_statements = State()


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

def tf_lobby_keyboard(players_count: int):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Присоединиться ({players_count})", callback_data="tf_join")
    builder.button(text="Выбрать режим и начать", callback_data="tf_choose_mode")
    builder.button(text="Отменить", callback_data="tf_cancel")
    builder.adjust(1)
    return builder.as_markup()


def tf_mode_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="2 Правды + 1 Ложь", callback_data="tf_mode:2T1L")
    builder.button(text="2 Лжи + 1 Правда", callback_data="tf_mode:2L1T")
    builder.button(text="1 Правда + 1 Ложь", callback_data="tf_mode:1T1L")
    builder.adjust(1)
    return builder.as_markup()


def tf_vote_keyboard(count: int):
    """Кнопки 1, 2, 3... для голосования"""
    builder = InlineKeyboardBuilder()
    for i in range(1, count + 1):
        builder.button(text=str(i), callback_data=f"tf_vote:{i}")
    builder.adjust(3)
    return builder.as_markup()





#главный код

async def check_game_timeout(chat_id: int):
    """Проверяет игру каждые 30 секунд. Если 5 минут тишины — удаляет."""
    while chat_id in games:
        await asyncio.sleep(30)
        
        game = games.get(chat_id)
        if not game:
            break
            
        last_activity = game.get("last_activity", time.time())
        if time.time() - last_activity > 300:  # 5 минут = 300 секунд
            try:
                await bot.send_message(chat_id, "⏰ Игра автоматически отменена из-за отсутствия активности (5 минут).")
            except:
                pass
            games.pop(chat_id, None)
            break

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
        "status": "lobby",
        "last_activity": time.time()
    }

    await message.answer(
        f"Игра «Шпион» создана!\nИгроков: 1\n\nЖми кнопку, чтобы присоединиться.",
        reply_markup=lobby_keyboard(1)
    )
    await state.set_state(GameStates.lobby)
    asyncio.create_task(check_game_timeout(chat_id))

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

@router.callback_query(F.data == "cancel_game")
async def cancel_game(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game:
        await callback.answer("Игры нет", show_alert=True)
        return

    # Хост или любой участник может отменить
    if callback.from_user.id != game["host"] and callback.from_user.id not in game["players"]:
        await callback.answer("Только участники могут отменить", show_alert=True)
        return

    del games[chat_id]
    await callback.message.edit_text("Игра отменена.")
    await callback.answer()

@router.callback_query(F.data == "start_game")
async def start_game(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game["host"] != callback.from_user.id:
        await callback.answer("Только хост может начать!", show_alert=True)
        return

    players = list(game["players"].items())
    if len(players) < 3:
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
    game["last_activity"] = time.time()
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
    game["last_activity"] = time.time()
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








@router.message(Command("falsegame"))
async def false_game(message: Message):
    if message.chat.type == "private":
        await message.answer("Играть можно только в группе!")
        return

    chat_id = message.chat.id
    if chat_id in games:
        await message.answer("В этом чате уже идёт другая игра!")
        return

    games[chat_id] = {
        "type": "truefalse",
        "host": message.from_user.id,
        "players": {message.from_user.id: message.from_user.full_name},
        "status": "lobby",
        "last_activity": time.time(),
        "mode": None,
        "statements": {},      # user_id: list of {"text": ..., "is_truth": bool}
        "order": [],
        "current_index": 0,
        "votes": {}
    }

    await message.answer(
        f"Игра «Правда / Ложь» создана!\nИгроков: 1\n\nЖми кнопку, чтобы присоединиться.",
        reply_markup=tf_lobby_keyboard(1)
    )
    asyncio.create_task(check_game_timeout(chat_id))


@router.callback_query(F.data == "tf_join")
async def tf_join(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    user = callback.from_user

    game = games.get(chat_id)
    if not game or game.get("type") != "truefalse" or game["status"] != "lobby":
        await callback.answer("Игра не найдена или уже началась", show_alert=True)
        return

    if user.id in game["players"]:
        await callback.answer("Ты уже в игре!")
        return

    game["players"][user.id] = user.full_name
    game["last_activity"] = time.time()
    count = len(game["players"])

    await callback.message.edit_text(
        f"Игра «Правда / Ложь»\nИгроков: {count}\n\nЖми кнопку, чтобы присоединиться.",
        reply_markup=tf_lobby_keyboard(count)
    )
    await callback.answer("Ты в игре!")


@router.callback_query(F.data == "tf_cancel")
async def tf_cancel(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game.get("type") != "truefalse":
        await callback.answer("Игры нет", show_alert=True)
        return

    if callback.from_user.id != game["host"] and callback.from_user.id not in game["players"]:
        await callback.answer("Только участники могут отменить", show_alert=True)
        return

    del games[chat_id]
    await callback.message.edit_text("Игра «Правда / Ложь» отменена.")
    await callback.answer()


@router.callback_query(F.data == "tf_choose_mode")
async def tf_choose_mode(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game.get("type") != "truefalse":
        await callback.answer("Игра не найдена", show_alert=True)
        return

    if game["host"] != callback.from_user.id:
        await callback.answer("Только хост может выбирать режим!", show_alert=True)
        return

    if len(game["players"]) < 2:
        await callback.answer("Нужно минимум 2 игрока!", show_alert=True)
        return

    await callback.message.edit_text(
        "Выберите режим игры:",
        reply_markup=tf_mode_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tf_mode:"))
async def tf_set_mode(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game.get("type") != "truefalse" or game["host"] != callback.from_user.id:
        await callback.answer("Нет доступа", show_alert=True)
        return

    mode = callback.data.split(":")[1]
    game["mode"] = mode
    game["status"] = "collecting"
    game["last_activity"] = time.time()

    if mode == "2T1L":
        instruction = "Пришли <b>2 правды и 1 ложь</b> в таком порядке:\n1. Правда\n2. Правда\n3. Ложь"
        needed = 3
        truth_positions = [0, 1]
    elif mode == "2L1T":
        instruction = "Пришли <b>2 лжи и 1 правду</b> в таком порядке:\n1. Ложь\n2. Ложь\n3. Правда"
        needed = 3
        truth_positions = [2]
    else:  # 1T1L
        instruction = "Пришли <b>1 правду и 1 ложь</b> в таком порядке:\n1. Правда\n2. Ложь"
        needed = 2
        truth_positions = [0]

    game["needed"] = needed
    game["truth_positions"] = truth_positions

    await callback.message.edit_text(
        "Режим выбран!\n\nСейчас каждому игроку в личку придёт задание.\n"
        "У вас есть время подготовить утверждения."
    )

    # Вот этот цикл должен быть внутри функции (с отступом)
    for user_id, name in game["players"].items():
        try:
            await bot.send_message(
                user_id,
                f"Твоя очередь готовить утверждения для игры «Правда / Ложь».\n\n"
                f"{instruction}\n\n"
                f"Просто напиши пронумерованный список, например:\n"
                f"1. Я люблю пиццу\n"
                f"2. Я был на Луне\n"
                f"3. У меня есть собака",
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                f"Не смог написать {name} в личку. Пусть сначала напишет боту /start"
            )

    await callback.answer()

# Приём утверждений в личку
@router.message(F.chat.type == "private")
async def receive_statements(message: Message):
    user_id = message.from_user.id

    # Ищем игру, в которой этот игрок участвует и статус collecting
    current_game = None
    current_chat = None
    for chat_id, game in games.items():
        if (game.get("type") == "truefalse" 
            and game["status"] == "collecting" 
            and user_id in game["players"]
            and user_id not in game["statements"]):
            current_game = game
            current_chat = chat_id
            break

    if not current_game:
        return   # просто игнорируем, если не ждём от него утверждений

    text = message.text.strip()
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    needed = current_game["needed"]
    if len(lines) < needed:
        await message.answer(f"Нужно ровно {needed} утверждения. Попробуй ещё раз.")
        return

    statements = []
    truth_positions = current_game["truth_positions"]

    for i in range(needed):
        clean = lines[i]
        if clean and clean[0].isdigit() and "." in clean[:3]:
            clean = clean.split(".", 1)[1].strip()

        is_truth = i in truth_positions
        statements.append({"text": clean, "is_truth": is_truth})

    current_game["statements"][user_id] = statements
    await message.answer("✅ Утверждения приняты! Жди начала игры.")

    # Проверяем, все ли сдали
    if len(current_game["statements"]) == len(current_game["players"]):
        await start_truefalse_round(current_chat)


async def start_truefalse_round(chat_id: int):
    game = games.get(chat_id)
    if not game:
        return

    game["status"] = "playing"
    game["order"] = list(game["players"].keys())
    random.shuffle(game["order"])
    game["current_index"] = 0
    game["last_activity"] = time.time()

    await bot.send_message(chat_id, "Все утверждения собраны!\nНачинаем через 5 секунд...")
    await asyncio.sleep(5)
    await next_truefalse_turn(chat_id)


async def next_truefalse_turn(chat_id: int):
    game = games.get(chat_id)
    if not game or game["status"] != "playing":
        return

    if game["current_index"] >= len(game["order"]):
        await bot.send_message(chat_id, "Игра окончена! Все ходы сделаны.")
        del games[chat_id]
        return

    user_id = game["order"][game["current_index"]]
    name = game["players"][user_id]
    statements = game["statements"][user_id].copy()
    random.shuffle(statements)          # перемешиваем перед показом

    game["current_statements"] = statements
    game["votes"] = {}
    game["last_activity"] = time.time()

    # Формируем текст
    mode = game["mode"]
    if mode == "2T1L":
        vote_for = "ЛОЖЬ"
    else:
        vote_for = "ПРАВДУ"

    text = f"Ход игрока: <b>{name}</b>\n\n"
    for i, st in enumerate(statements, 1):
        text += f"{i}. {st['text']}\n"

    text += f"\nГолосуйте, какая из них <b>{vote_for}</b>:"

    await bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        reply_markup=tf_vote_keyboard(len(statements))
    )


@router.callback_query(F.data.startswith("tf_vote:"))
async def tf_process_vote(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)

    if not game or game.get("type") != "truefalse" or game["status"] != "playing":
        await callback.answer("Сейчас нет активного голосования", show_alert=True)
        return

    voter_id = callback.from_user.id
    if voter_id not in game["players"]:
        await callback.answer("Ты не в этой игре!", show_alert=True)
        return

    if voter_id in game["votes"]:
        await callback.answer("Ты уже проголосовал!", show_alert=True)
        return

    choice = int(callback.data.split(":")[1])
    game["votes"][voter_id] = choice
    game["last_activity"] = time.time()
    await callback.answer("Голос принят!")

    # Сколько человек должны проголосовать (все, кроме того, чьи утверждения сейчас)
    current_speaker = game["order"][game["current_index"]]
    needed_votes = len(game["players"]) - 1

    print(f"Голосов: {len(game['votes'])} из {needed_votes}")  # для отладки

    if len(game["votes"]) >= needed_votes:
        await finish_truefalse_vote(chat_id, callback.message)


async def finish_truefalse_vote(chat_id: int, message: Message):
    game = games.get(chat_id)
    if not game:
        return

    try:
        from collections import Counter
        results = Counter(game["votes"].values())
        most_voted = results.most_common(1)[0][0] if results else 1

        statements = game["current_statements"]

        if game["mode"] == "2T1L":
            correct = [i+1 for i, st in enumerate(statements) if not st["is_truth"]]
        else:
            correct = [i+1 for i, st in enumerate(statements) if st["is_truth"]]

        text = f"Результаты голосования:\nВыбрали вариант <b>{most_voted}</b>\n\n"
        text += "Правильный ответ: " + ", ".join(map(str, correct)) + "\n\n"

        for i, st in enumerate(statements, 1):
            mark = "✅ Правда" if st["is_truth"] else "❌ Ложь"
            text += f"{i}. {st['text']} — {mark}\n"

        await message.edit_text(text, parse_mode="HTML")

    except Exception as e:
        await bot.send_message(chat_id, f"Ошибка при подведении итогов: {e}")

    # Переходим к следующему
    game["current_index"] += 1
    await asyncio.sleep(3)
    await next_truefalse_turn(chat_id)

















@router.message(Command("balance"))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    balance = crypto_balances.get(user_id, 0)
    await message.answer(
        f"💰 Твой баланс: <b>{balance}</b> БотКоин",
        parse_mode="HTML"
    )


@router.message(Command("give"))
async def cmd_give(message: Message):
    """Только админ выдаёт БотКоины"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только админ может выдавать БотКоины.")
        return

    args = message.text.split()

    # Ответом на сообщение: /give 100
    if message.reply_to_message and len(args) == 2:
        try:
            amount = int(args[1])
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.first_name
        except ValueError:
            await message.answer("Использование: /give <количество> (ответом на сообщение)")
            return
    # /give ID количество
    elif len(args) == 3:
        try:
            target_id = int(args[1])
            amount = int(args[2])
            target_name = str(target_id)
        except ValueError:
            await message.answer("Использование: /give <id> <количество>")
            return
    else:
        await message.answer(
            "Как выдать БотКоины:\n"
            "1. Ответить на сообщение: /give 100\n"
            "2. Или: /give <id> 100"
        )
        return

    if amount <= 0:
        await message.answer("Количество должно быть больше 0.")
        return

    crypto_balances[target_id] = crypto_balances.get(target_id, 0) + amount

    await message.answer(
        f"✅ Выдано <b>{amount}</b> БотКоин пользователю {target_name}\n"
        f"Его баланс: {crypto_balances[target_id]} БотКоин",
        parse_mode="HTML"
    )


@router.message(Command("pay"))
async def cmd_pay(message: Message):
    """Перевод БотКоинов другому"""
    user_id = message.from_user.id
    args = message.text.split()

    # Ответом: /pay 50
    if message.reply_to_message and len(args) == 2:
        try:
            amount = int(args[1])
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.first_name
        except ValueError:
            await message.answer("Использование: /pay <количество> (ответом на сообщение)")
            return
    # /pay ID 50
    elif len(args) == 3:
        try:
            target_id = int(args[1])
            amount = int(args[2])
            target_name = str(target_id)
        except ValueError:
            await message.answer("Использование: /pay <id> <количество>")
            return
    else:
        await message.answer(
            "Как перевести:\n"
            "1. Ответить на сообщение: /pay 50\n"
            "2. Или: /pay <id> 50"
        )
        return

    if amount <= 0:
        await message.answer("Сумма должна быть больше 0.")
        return

    if target_id == user_id:
        await message.answer("Нельзя переводить самому себе.")
        return

    sender_balance = crypto_balances.get(user_id, 0)
    if sender_balance < amount:
        await message.answer(f"Недостаточно БотКоинов. У тебя: {sender_balance}")
        return

    crypto_balances[user_id] = sender_balance - amount
    crypto_balances[target_id] = crypto_balances.get(target_id, 0) + amount

    await message.answer(
        f"✅ Переведено <b>{amount}</b> БотКоин → {target_name}\n"
        f"Твой баланс: {crypto_balances[user_id]} БотКоин",
        parse_mode="HTML"
    )

@dp.message(F.text.lower() == "рулетка")
async def ryletka(message: Message):
    user_id = message.from_user.id
    rylet = random.randint(1, 6)
    sender_balance = crypto_balances.get(user_id, 0)
    live = 0

    if sender_balance < 500:
        await message.answer("недостаточно денег на балансе, нужно минимум 500")
        live = 2
    elif rylet == 1:
        await message.answer("пустой щелчок, вы выжили")
        crypto_balances[user_id] = sender_balance + 50
    elif rylet == 2:
        await message.answer("пустое клацанье револьвера пронеслось по комнате, вы выжили")
        crypto_balances[user_id] = sender_balance + 50
    elif rylet == 3:
        await message.answer("курок был нажат, но сегодня удача на вашей стороне, вы выжили")
        crypto_balances[user_id] = sender_balance + 50
    elif rylet == 4:
        await message.answer("вот это смельчак, вы выжили, но больше так не делайте, подумайте о маме и папе")
        crypto_balances[user_id] = sender_balance + 50
    elif rylet == 5:
        await message.answer("вам повезло, ведь вы выжили")
        crypto_balances[user_id] = sender_balance + 50
    else:
        await message.answer("прозвучал выстрел, удача на этот раз обернулась вам спинной, вы мертвы")
        crypto_balances[user_id] = sender_balance - 500
        live = 1
    if live == 0:
        await message.answer("к вашему счету добавилось 50 Боткоинов")
    elif live == 1:
        await message.answer("с вашего баланса сняли 500 Боткоинов")
    else:
        await message.answer("нищета")

@router.message(Command("lottery"))
async def cmd_lottery(message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    # Проверяем формат: /lottery сумма ц1 ц2 ц3
    if len(args) != 5:
        await message.answer(
            "Использование:\n"
            "<code>/lottery сумма цифра1 цифра2 цифра3</code>\n\n"
            "Пример: <code>/lottery 50 2 4 6</code>\n"
            "Цифры должны быть разными от 1 до 6",
            parse_mode="HTML"
        )
        return

    try:
        amount = int(args[1])
        nums = [int(args[2]), int(args[3]), int(args[4])]
    except ValueError:
        await message.answer("Сумма и цифры должны быть числами.")
        return

    # Проверки
    if amount <= 0:
        await message.answer("Ставка должна быть больше 0.")
        return

    if len(set(nums)) != 3:
        await message.answer("Все три цифры должны быть разными!")
        return

    if not all(1 <= n <= 6 for n in nums):
        await message.answer("Цифры должны быть от 1 до 6.")
        return

    balance = crypto_balances.get(user_id, 0)
    if balance < amount:
        await message.answer(f"Недостаточно БотКоинов. У тебя: {balance}")
        return

    # Списываем ставку
    crypto_balances[user_id] = balance - amount

    # Генерируем 3 случайных смайлика
    emojis = ["🍇", "🍌", "🍏"]
    results = [random.choice(emojis) for _ in range(3)]

    # Считаем совпадения
    from collections import Counter
    counts = Counter(results)
    max_count = max(counts.values())

    text = f"Твоя ставка: <b>{amount}</b> БотКоин\n\n"
    text += f"{nums[0]} → {results[0]}\n"
    text += f"{nums[1]} → {results[1]}\n"
    text += f"{nums[2]} → {results[2]}\n\n"

    if max_count == 3:
        win = amount * 3
        crypto_balances[user_id] += win
        text += f"🎉 Тройка! Выигрыш ×3\nТы получил <b>{win}</b> БотКоин"
    elif max_count == 2:
        win = amount * 2
        crypto_balances[user_id] += win
        text += f"✨ Пара! Выигрыш ×2\nТы получил <b>{win}</b> БотКоин"
    else:
        text += "😔 Ничего не совпало. Ставка сгорела."

    text += f"\n\nТвой баланс: <b>{crypto_balances[user_id]}</b> БотКоин"

    await message.answer(text, parse_mode="HTML")






















@router.message(Command("send"))
async def admin_send(message: Message, command: CommandObject):
    """Отправить сообщение в группу. Использование: /send текст"""
    if message.from_user.id != ADMIN_ID:
        return
    
    if not command.args:
        await message.reply("Использование: /send текст сообщения")
        return
    
    try:
        await bot.send_message(GROUP_ID, command.args)
        await message.reply("✅ Отправлено в группу")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


@router.message(Command("sendid"))
async def admin_send_id(message: Message, command: CommandObject):
    """Отправить сообщение пользователю. Использование: /sendid 123456789 Привет"""
    if message.from_user.id != ADMIN_ID:
        return
    
    if not command.args:
        await message.reply("Использование: /sendid ID текст")
        return
    
    parts = command.args.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Нужно: /sendid ID текст")
        return
    
    try:
        target_id = int(parts[0])
        text = parts[1]
        await bot.send_message(target_id, text)
        await message.reply(f"✅ Отправлено пользователю {target_id}")
    except ValueError:
        await message.reply("ID должен быть числом")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

# Регистрируем роутер в диспетчере
dp.include_router(router)

# Обработчик команды /start на aiogram
@router.message(CommandStart())
async def start_command(message: Message):
    await message.reply("Привет! Я работаю круглосуточно на Render!")

async def main():
    print("Бот запускается...")
    # Запускаем чтение обновлений Telegram
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    # Запускаем веб-сервер Flask в отдельном потоке для Render
    t = Thread(target=run_flask)
    t.daemon = True  # поток закроется автоматически при остановке бота
    t.start()
    
    # Запускаем асинхронного бота aiogram
    asyncio.run(main())
