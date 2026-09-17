from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# def main_menu_keyboard() -> InlineKeyboardMarkup:
#     """Главное меню"""
#     builder = InlineKeyboardBuilder()
#     builder.button(text="📊 Asset price", callback_data="price")
#     builder.button(text="📬 Price alerts", callback_data="subscription_menu")
#     builder.button(text="📈 Price chart", callback_data="pricechart")
#     builder.button(text="⚖️ Assets comparison", callback_data="compare")
#     builder.button(text="🧮 Asset key metrics", callback_data="metrics")
#     builder.button(text="📄 Asset general info", callback_data="info")
#     builder.adjust(2)
#     return builder.as_markup()

# def subscription_menu_keyboard(has_subscription: bool = False) -> InlineKeyboardMarkup:
#     """Меню управления рассылкой"""
#     builder = InlineKeyboardBuilder()
#     if has_subscription:
#         builder.button(text="✅ Subscription is active", callback_data="dummy")
#         builder.button(text="⏹ Unsubscribe", callback_data="unsubscribe")
#     else:
#         builder.button(text="🕒 Subscribe", callback_data="subscribe")
    

#     builder.button(text="🔙 Main menu", callback_data="main_menu")
#     builder.adjust(1)
#     return builder.as_markup()

# def portfolio_menu_keyboard(has_portfolio: bool = False) -> InlineKeyboardMarkup:
#     """Меню управления рассылкой"""
#     builder = InlineKeyboardBuilder()
#     if has_portfolio:
#         builder.button(text="✅ Portfolio is active", callback_data="dummy")
#         builder.button(text="⏹ Add to portfolio", callback_data="add_to_portfolio")
#         builder.button(text="⏹ Remove from portfolio", callback_data="Remove_from_portfolio")
#     else:
#         builder.button(text="🕒 Add to portfolio", callback_data="add_to_portfolio")
    

#     builder.button(text="🔙 Main menu", callback_data="main_menu")
#     builder.adjust(1)
#     return builder.as_markup()



#Не функционально, сейчас весь функционал на reply