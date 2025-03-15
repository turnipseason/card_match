""" Инструменты, которые будет пособен использовать агент """

from langchain.tools import tool
from data.db_connect import DatabaseConnection

db_con = DatabaseConnection()

@tool
def get_user_info(passport_id: str):
    """
    Возвращает информацию о предпочтениях пользователя, типом самых частых транзацкий и т.д.
    :return:
    """
    ### TODO

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