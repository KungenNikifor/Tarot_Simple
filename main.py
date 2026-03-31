import asyncio
import random
import logging
import aiohttp
import os
from dotenv import load_dotenv
from aiohttp import web

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InputMediaPhoto

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ НА RENDER ---
async def handle_healthcheck(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', os.getenv('PORT', 10000))
    await site.start()
# ----------------------------------

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
    adjusting_card = State()


async def get_ai_interpretation(question, cards):
    try:
        async with aiohttp.ClientSession() as session:
            prompt = (f"Ты мудрый таролог. Вопрос: '{question}'. "
                      f"Карты: {', '.join(cards)}. Дай краткую трактовку (до 700 симв).")
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            gen_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
            async with session.post(gen_url, json=payload) as resp:
                result = await resp.json()
                if 'candidates' in result:
                    return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    logging.error(f"Gemini Error: {result}")
                    return "ИИ временно недоступен. Проверьте API ключ."
    except Exception as e:
        logging.error(f"Request Error: {e}")
        return "Ошибка связи с космосом..."


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder().row(
        types.InlineKeyboardButton(text="🔮 Начать гадание", callback_data="start_divination"))
    await message.answer("Добро пожаловать в обитель Таро.", reply_markup=builder.as_markup())
    await state.set_state(TarotSteps.waiting_for_start)


@dp.callback_query(F.data == "start_divination")
async def ask_for_question(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Сформулируйте свой вопрос:")
    await state.set_state(TarotSteps.waiting_for_question)


@dp.message(TarotSteps.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
    await state.update_data(user_question=message.text)
    builder = InlineKeyboardBuilder().row(
        types.InlineKeyboardButton(text="🎨 Классика", callback_data="deck_classic"),
        types.InlineKeyboardButton(text="🌑 Темная", callback_data="deck_dark")
    )
    await message.answer("Выберите стиль колоды:", reply_markup=builder.as_markup())
    await state.set_state(TarotSteps.choosing_deck)


@dp.callback_query(F.data.startswith("deck_"), TarotSteps.choosing_deck)
async def select_deck(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(selected_deck=callback.data.split("_")[1], chosen_cards=[])
    builder = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🃏 Тянуть карту", callback_data="draw_card"))
    await callback.message.edit_text("Пора вытянуть 3 карты.", reply_markup=builder.as_markup())
    await state.set_state(TarotSteps.choosing_cards)


@dp.callback_query(F.data == "draw_card", TarotSteps.choosing_cards)
async def start_adjusting(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chosen = data.get('chosen_cards', [])
    available = [c for c in TAROT_DECK if c not in [x['name'] for x in chosen]]
    new_card_name = random.choice(available)
    await state.update_data(temp_card={"name": new_card_name, "orientation": "Прямая"})

    builder = InlineKeyboardBuilder().row(
        types.InlineKeyboardButton(text="🔄 Перевернуть", callback_data="flip_card"),
        types.InlineKeyboardButton(text="✅ Оставить", callback_data="confirm_card")
    )
    await callback.message.edit_text(f"Выпала карта: **{new_card_name}**\nПоложение: **Прямая**",
                                     parse_mode="Markdown", reply_markup=builder.as_markup())
    await state.set_state(TarotSteps.adjusting_card)


@dp.callback_query(F.data == "flip_card", TarotSteps.adjusting_card)
async def flip(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    temp = data['temp_card']
    temp['orientation'] = "Перевернутая" if temp['orientation'] == "Прямая" else "Прямая"
    await state.update_data(temp_card=temp)
    builder = InlineKeyboardBuilder().row(
        types.InlineKeyboardButton(text="🔄 Перевернуть", callback_data="flip_card"),
        types.InlineKeyboardButton(text="✅ Оставить", callback_data="confirm_card")
    )
    await callback.message.edit_text(f"Выпала карта: **{temp['name']}**\nПоложение: **{temp['orientation']}**",
                                     parse_mode="Markdown", reply_markup=builder.as_markup())


@dp.callback_query(F.data == "confirm_card", TarotSteps.adjusting_card)
async def confirm(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chosen = data.get('chosen_cards', [])
    chosen.append(data['temp_card'])
    await state.update_data(chosen_cards=chosen)

    if len(chosen) < 3:
        builder = InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="🃏 Следующая карта", callback_data="draw_card"))
        await callback.message.edit_text(f"Выбрано {len(chosen)}/3", reply_markup=builder.as_markup())
        await state.set_state(TarotSteps.choosing_cards)
    else:
        await callback.message.edit_text("⏳ Все карты выбраны. Изучаю знаки судьбы...")
        cards_str = [f"{c['name']} ({c['orientation']})" for c in chosen]
        interpretation = await get_ai_interpretation(data['user_question'], cards_str)

        media = []
        for c in chosen:
            p = f"images/{data['selected_deck']}/{c['name']}.jpg"
            if os.path.exists(p): media.append(InputMediaPhoto(media=types.FSInputFile(p)))

        if media: await callback.message.answer_media_group(media=media)

        builder = InlineKeyboardBuilder().row(
            types.InlineKeyboardButton(text="✨ Новый запрос", callback_data="start_divination"))
        await callback.message.answer(f"🔮 **Расклад:**\n" + "\n".join(cards_str) + f"\n\n{interpretation}",
                                      parse_mode="Markdown", reply_markup=builder.as_markup())
        await state.clear()


# 4. ЗАПУСК
async def main():
    # Запускаем веб-сервер и бота одновременно
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())