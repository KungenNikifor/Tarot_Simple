import asyncio
import random
import logging
import aiohttp
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InputMediaPhoto

load_dotenv()
TELEGRAM_TOKEN = os.getenv('7999144564:AAHT7FKTqCR2lr1uuXTTmtJ9zUOtb61fSIg')
GEMINI_KEY = os.getenv('AIzaSyC7fo9lVtgNtQ56VTZfZU3ivKuOd7GQzKM')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Список карт
TAROT_DECK = [
    "Шут", "Маг", "Жрица", "Императрица", "Император", "Иерофант", "Влюбленные", "Колесница", "Сила",
    "Отшельник", "Колесо Фортуны", "Справедливость", "Повешенный", "Смерть", "Умеренность", "Дьявол",
    "Башня", "Звезда", "Луна", "Солнце", "Суд", "Мир", "Король Жезлов", "Королева Жезлов", "Рыцарь Жезлов",
    "Паж Жезлов", "Десятка Жезлов", "Девятка Жезлов", "Восьмерка Жезлов", "Семерка Жезлов", "Шестерка Жезлов",
    "Пятерка Жезлов", "Четверка Жезлов", "Тройка Жезлов", "Двойка Жезлов", "Туз Жезлов", "Король Кубков",
    "Королева Кубков", "Рыцарь Кубков", "Паж Кубков", "Десятка Кубков", "Девятка Кубков", "Восьмерка Кубков",
    "Семерка Кубков", "Шестерка Кубков", "Пятерка Кубков", "Четверка Кубков", "Тройка Кубков", "Двойка Кубков",
    "Туз Кубков", "Король Мечей", "Королева Мечей", "Рыцарь Мечей", "Паж Мечей", "Десятка Мечей", "Девятка Мечей",
    "Восьмерка Мечей", "Семерка Мечей", "Шестерка Мечей", "Пятерка Мечей", "Четверка Мечей", "Тройка Мечей",
    "Двойка Мечей", "Туз Мечей", "Король Пентаклей", "Королева Пентаклей", "Рыцарь Пентаклей", "Паж Пентаклей",
    "Десятка Пентаклей", "Девятка Пентаклей", "Восьмерка Пентаклей", "Семерка Пентаклей", "Шестерка Пентаклей",
    "Пятерка Пентаклей", "Четверка Пентаклей", "Тройка Пентаклей", "Двойка Пентаклей", "Туз Пентаклей"
]


class TarotSteps(StatesGroup):
    waiting_for_start = State()
    waiting_for_question = State()
    choosing_deck = State()
    choosing_cards = State()


async def get_ai_interpretation(question, cards):
    try:
        async with aiohttp.ClientSession() as session:
            # Строгий промпт на краткость
            prompt = (
                f"Ты лаконичный и мудрый таролог. Вопрос клиента: '{question}'. "
                f"Выпавшие карты: {', '.join(cards)}. Дай краткую, но глубокую трактовку. "
                f"Максимум 700 символов. Пиши сразу суть."
            )
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            gen_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

            async with session.post(gen_url, json=payload) as resp:
                result = await resp.json()
                return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return "Карты молчат... Попробуйте еще раз через минуту."


# 1. СТАРТОВОЕ МЕНЮ
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔮 Начать гадание", callback_data="start_divination"))
    await message.answer("Добро пожаловать в обитель Таро. Готовы узнать правду?", reply_markup=builder.as_markup())
    await state.set_state(TarotSteps.waiting_for_start)


# ПЕРЕХОД К ВОПРОСУ
@dp.callback_query(F.data == "start_divination")
async def ask_for_question(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Сформулируйте свой вопрос и напишите его мне:")
    await state.set_state(TarotSteps.waiting_for_question)


@dp.message(TarotSteps.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
    await state.update_data(user_question=message.text)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🎨 Классика", callback_data="deck_classic"))
    builder.row(types.InlineKeyboardButton(text="🌑 Темная", callback_data="deck_dark"))
    await message.answer("Выберите стиль колоды:", reply_markup=builder.as_markup())
    await state.set_state(TarotSteps.choosing_deck)


@dp.callback_query(F.data.startswith("deck_"), TarotSteps.choosing_deck)
async def select_deck(callback: types.CallbackQuery, state: FSMContext):
    deck_type = callback.data.split("_")[1]
    await state.update_data(selected_deck=deck_type, chosen_cards=[])
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🃏 Вытянуть карту", callback_data="draw_card"))
    await callback.message.edit_text(f"Колода: {deck_type}. Пора тянуть карты (нужно 3).",
                                     reply_markup=builder.as_markup())
    await state.set_state(TarotSteps.choosing_cards)


@dp.callback_query(F.data == "draw_card", TarotSteps.choosing_cards)
async def draw_card(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chosen_cards = data.get('chosen_cards', [])

    available = [c for c in TAROT_DECK if c not in [x['name'] for x in chosen_cards]]
    new_card = random.choice(available)
    orientation = random.choice(["Прямая", "Перевернутая"])

    chosen_cards.append({"name": new_card, "orientation": orientation})
    await state.update_data(chosen_cards=chosen_cards)

    if len(chosen_cards) < 3:
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="🃏 Тянуть еще", callback_data="draw_card"))
        await callback.message.edit_text(f"Выбрано: {len(chosen_cards)} из 3", reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text("⏳ Изучаю знаки судьбы...")

        cards_str = [f"{c['name']} ({c['orientation']})" for c in chosen_cards]
        interpretation = await get_ai_interpretation(data['user_question'], cards_str)

        # Фото
        deck = data['selected_deck']
        media = []
        for c in chosen_cards:
            path = f"images/{deck}/{c['name']}.jpg"
            if os.path.exists(path):
                media.append(InputMediaPhoto(media=types.FSInputFile(path)))

        if media:
            await callback.message.answer_media_group(media=media)

        # 2. КНОПКА "НОВЫЙ ЗАПРОС" В КОНЦЕ
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="✨ Новый запрос", callback_data="start_divination"))

        final_text = f"🔮 **Ваш расклад:**\n" + "\n".join(cards_str) + f"\n\n{interpretation}"
        await callback.message.answer(final_text, parse_mode="Markdown", reply_markup=builder.as_markup())
        await state.set_state(TarotSteps.waiting_for_start)


# 4. ЗАПУСК
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())