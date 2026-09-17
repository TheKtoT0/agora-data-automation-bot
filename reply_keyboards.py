from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="/price"), KeyboardButton(text="/metrics")],
        [KeyboardButton(text="/info"), KeyboardButton(text="/pricechart")],
        [KeyboardButton(text="/get_report"), KeyboardButton(text="/compare")],
        [KeyboardButton(text="/set_timezone"), KeyboardButton(text="/get_timezone")],
        [KeyboardButton(text="/add_to_portfolio"), KeyboardButton(text="/remove_from_portfolio")],
        [KeyboardButton(text="/portfolio"), KeyboardButton(text="/get_report_portfolio")],
        [KeyboardButton(text="/subscribe_report_ticker"), KeyboardButton(text="/set_alert")],
        [KeyboardButton(text="/help")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )