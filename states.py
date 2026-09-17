from aiogram.fsm.state import State, StatesGroup

class AssetStates(StatesGroup):
    """Основная группа состояний для работы с тикерами"""
    
    waiting_for_ticker = State()           # Ожидаем один тикер (price, chart, metrics и т.д.)
    waiting_for_two_tickers = State()      # Ожидаем два тикера (для /compare)
    # Потом добавить:
    waiting_for_timezone = State()
    waiting_for_quantity = State()       # для добавления в портфель
    waiting_for_alert_command = State()    # для алертов

    waiting_for_params = State()

    waiting_for_schedule_command_price = State()
    waiting_for_schedule_command_chart = State()
    waiting_for_set_alert = State()
    waiting_for_schedule_time = State()   # для даннных по расписанию, время отправки
    waiting_for_schedule_ticker = State()   # для данных по расписанию, тикеры
    waiting_for_schedule_subscription = State()

    waiting_for_schedule_command_report_ticker = State()
    waiting_for_schedule_command_report_portfolio = State()
    waiting_for_add_to_portfolio = State()
    waiting_for_remove_from_portfolio = State()

    waiting_for_remove_subscription = State()
    waiting_for_remove_alert = State()