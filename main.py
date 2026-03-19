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

# --- ИНИЦИАЛИЗАЦИЯ ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')

if not TELEGRAM_TOKEN or not GEMINI_KEY:
    exit("Критическая ошибка: Токены не найдены в .env!")

# Настройка логирования (вывод в консоль)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- КОНСТАНТЫ ---
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
    waiting_for_question = State()
    choosing_cards = State()


# --- ЛОГИКА GEMINI AI ---
async def get_ai_interpretation(question, cards):
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            # Динамический поиск живой модели
            async with session.get(list_url) as resp:
                data = await resp.json()
                models = [m['name'] for m in data.get('models', []) if
                          'generateContent' in m.get('supportedGenerationMethods', [])]
                if not models: return "Ошибка: Доступные модели не найдены."
                active_model = models[0]

            # Запрос на генерацию
            gen_url = f"https://generativelanguage.googleapis.com/v1beta/{active_model}:generateContent?key={GEMINI_KEY}"
            prompt = f"Ты профессиональный таролог. Вопрос клиента: '{question}'. Выпали карты: {', '.join(cards)}. На основании признанных экспертов в области Таро, дай глубокую и мудрую интерпретацию на русском языке."

            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            async with session.post(gen_url, json=payload) as resp:
                result = await resp.json()
                if 'candidates' in result:
                    return result['candidates'][0]['content']['parts'][0]['text']
                return f"ИИ не смог дать ответ: {result.get('error', {}).get('message', 'Неизвестная ошибка')}"
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "Простите, связь с тонким миром прервалась. Попробуйте позже."


# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("✨ Добро пожаловать в обитель Таро. О чем вы хотите спросить карты?")
    await state.set_state(TarotSteps.waiting_for_question)


@dp.message(TarotSteps.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
    await state.update_data(user_question=message.text, chosen_cards=[])
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔮 Коснуться колоды", callback_data="draw_card"))
    await message.answer(f"Ваш вопрос: «{message.text}»\nВыберите 3 карты для расклада.",
                         reply_markup=builder.as_markup())
    await state.set_state(TarotSteps.choosing_cards)


@dp.callback_query(F.data.in_(["draw_card", "flip_card"]), TarotSteps.choosing_cards)
async def handle_card_selection(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chosen_cards = data.get('chosen_cards', [])

    if callback.data == "draw_card":
        picked_names = [c['name'] for c in chosen_cards]
        available = [c for c in TAROT_DECK if c not in picked_names]
        current_card = random.choice(available)
        orientation = "Положение1"
        await state.update_data(current_card=current_card, current_orientation=orientation)
    else:
        orientation = "Положение2" if data.get('current_orientation') == "Положение1" else "Положение1"
        await state.update_data(current_orientation=orientation)

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔄 Перевернуть", callback_data="flip_card"))
    builder.row(types.InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_card"))

    icon = "⬆️" if orientation == "Положение1" else "⬇️"
    await callback.message.edit_text(
        f"🔮 Карта №{len(chosen_cards) + 1} выбрана.\nПоложение: **{orientation}** {icon}\n\nВы можете изменить положение перед подтверждением.",
        reply_markup=builder.as_markup(), parse_mode="Markdown"
    )


@dp.callback_query(F.data == "confirm_card", TarotSteps.choosing_cards)
async def confirm_card(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chosen_cards = data.get('chosen_cards', [])
    chosen_cards.append({"name": data.get('current_card'), "orientation": data.get('current_orientation')})
    await state.update_data(chosen_cards=chosen_cards)

    if len(chosen_cards) < 3:
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="🃏 Следующая карта", callback_data="draw_card"))
        await callback.message.edit_text(f"Карта №{len(chosen_cards)} принята. Продолжаем?",
                                         reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text("⏳ Вскрываем карты и трактуем смыслы...")

        cards_for_ai = [f"{c['name']} ({c['orientation']})" for c in chosen_cards]
        interpretation = await get_ai_interpretation(data['user_question'], cards_for_ai)

        # Отправка изображений
        media = []
        for card in chosen_cards:
            path = f"images/{card['name']}.jpg"
            if os.path.exists(path):
                media.append(InputMediaPhoto(media=types.FSInputFile(path)))

        if media:
            await callback.message.answer_media_group(media=media)

        # Финальный текст
        header = "🔮 **Ваш расклад готов:**\n" + "\n".join([f"• {c['name']} ({c['orientation']})" for c in chosen_cards])
        full_response = f"{header}\n\n{interpretation}"

        for i in range(0, len(full_response), 4000):
            await callback.message.answer(full_response[i:i + 4000], parse_mode=None)

        await state.clear()

# 4. ЗАПУСК
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())