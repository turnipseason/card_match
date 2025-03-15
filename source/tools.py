""" Инструменты, которые будет пособен использовать агент """

from langchain.tools import tool
from data.db_connect import DatabaseConnection

db_con = DatabaseConnection()

@tool
def get_user_preferences(user_passport: str):
    """
    Получает информацию о предпочтениях пользователя, запрашивая её в БД.

    Args:
        user_passport (str): Серия и номер паспорта клиента.

    Returns:
        dict: Данные о клиенте.
    """
    answer = db_con.get_user_preferences(user_passport)
    return answer

@tool
def get_user_cashback(user_passport: str):
    """
    Получает информацию о кэшбеке, доступном пользователю, запрашивая её в БД.

    Args:
        user_passport (str): Серия и номер паспорта клиента.

    Returns:
        dict: Кэшбек по всем картам клиента.
    """
    answer = db_con.get_user_cashback(user_passport)
    print("\033[92m" + "Bot requested get_user_cashback" + "\033[0m")
    return answer

@tool
def get_all_cards() -> list:
    """
    Возвращает информацию обо всех типах карт из таблицы card.
    Если пользователь пишет, что ему нужен конкретный банк {bank} - возвращай карты из этого банка.

    Returns:
        list: Список всех существующих карт с информацией о них
    """
    answer = db_con.get_all_cards()
    print("\033[92m" + "Bot requested get_all_cards" + "\033[0m")
    return answer

@tool
def get_user_cards(user_passport: str) -> list:
    """
    Возвращай по запросу пользователя информацию обо всех используемых им картах.
    В том числе -- конкретные условия по его картам, такие как точные расчеты по минимальной сумме за кредит.

    Args:
    user_passport (str): Серия и номер паспорта клиента.

    Returns:
        list: Список словарей с детальной информацией по картам клиента
    """
    print(f"Паспорт пользователя: {user_passport}")
    answer = db_con.get_client_cards(user_passport)
    print(f"Вот такие карты: {answer}")
    print("\033[92m" + f"Bot requested get_all_user_cards" + "\033[0m")
    return answer