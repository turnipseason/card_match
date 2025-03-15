import psycopg2
import os
from dotenv import load_dotenv
from psycopg2 import sql


class DatabaseConnection():
    def __init__(self):
        load_dotenv("config/db_env.env")
        self.conn_params = {
            'dbname': os.getenv("DB_NAME"),
            'user': os.getenv("USER"),
            'password': os.getenv("PASSWORD"),
            'host': os.getenv("HOST"),
            'port': os.getenv("PORT")
        }
        self.connection = psycopg2.connect(**self.conn_params)

    def close_connection(self):
        self.connection.close()

    def get_all_bd_users(self):
        cursor = self.connection.cursor()
        rows = None
        try:
            cursor.execute("SELECT * from client")
            rows = cursor.fetchall()
        except Exception as e:
            print(f"Возникла ошибка: {e}")
        cursor.close()
        return rows

    def get_all_cards(self) -> list:
        """
        Возвращает все карты из таблицы card.

        Returns:
            list: Список словарей с информацией о картах.
        """
        cards = []
        cursor = None

        try:
            cursor = self.connection.cursor()
            query = sql.SQL("""
                SELECT 
                    id, bank_name, name, min_rate, max_rate, 
                    annual_fee, psk, grace_period, cashback, bonus, max_reward
                FROM 
                    card
            """)

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                card_details = {
                    "id": row[0],
                    "bank_name": row[1],
                    "name": row[2],
                    "min_rate": row[3],
                    "max_rate": row[4],
                    "annual_fee": row[5],
                    "psk": row[6],
                    "grace_period": row[7],
                    "cashback": row[8],
                    "bonus": row[9],
                    "max_reward": row[10]
                }
                cards.append(card_details)

        except Exception as e:
            print(f"Возникла ошибка: {e}")
        finally:
            if cursor:
                cursor.close()
        return cards

    def get_client_cards(self, passport_id):
        """
        Возвращаем все карты клиента по его паспорту.

        Args:
            passport_id (str): Серия и номер паспорта клиента.

        Returns:
            list: Список словарей с детальной информацией по картам клиента.
        """

        # Пустой список для сохранения результатов
        client_cards = []
        cursor = None

        try:
            cursor = self.connection.cursor()
            query = sql.SQL("""
                SELECT 
                    c.id, c.bank_name, c.name, c.min_rate, c.max_rate, 
                    c.annual_fee, c.psk, c.grace_period, c.cashback, c.bonus,
                    c.max_reward, 
                    cc.rate, cc.annual_fee AS client_annual_fee, cc.psk AS client_psk,
                    cc.grace_period AS client_grace_period, cc.credit_limit, 
                    pc.name AS usual_purchase
                FROM 
                    client_card cc
                JOIN 
                    card c ON cc.card_id = c.id
                LEFT JOIN 
                    purchase_category pc ON cc.usual_purchase = pc.id
                WHERE 
                    cc.passport_id = %s
            """)

            cursor.execute(query, (passport_id,))
            rows = cursor.fetchall()
            print(rows)

            for row in rows:
                card_details = {
                    "card_id": row[0],
                    "bank_name": row[1],
                    "card_name": row[2],
                    "min_rate": row[3],
                    "max_rate": row[4],
                    "annual_fee": row[5],
                    "psk": row[6],
                    "grace_period": row[7],
                    "cashback": row[8],
                    "bonus": row[9],
                    "max_reward": row[10],
                    "client_rate": row[11],
                    "client_annual_fee": row[12],
                    "client_psk": row[13],
                    "client_grace_period": row[14],
                    "credit_limit": row[15],
                    "usual_purchase": row[16]
                }
                client_cards.append(card_details)
                print(f"Карты клиента: {client_cards}")

        except Exception as e:
            print(f"Возникла ошибка: {e}")
        finally:
            if cursor:
                cursor.close()
        return client_cards

