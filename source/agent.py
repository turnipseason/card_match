"""
Основная логика работы
"""
import os

from langchain_gigachat.chat_models import GigaChat
from dotenv import load_dotenv

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from source.prompts import system_prompt

from source.tools import get_all_cards, get_user_info, get_user_cards

# Загружаем переменные окружения
load_dotenv("config/ggc_env.env")

# Инициализируем модель GigaChat
model = GigaChat(
    credentials=os.getenv("GIGACHAT_API_CREDENTIALS"),
    scope=os.getenv("GIGACHAT_API_SCOPE"),
    model=os.getenv("GIGACHAT_MODEL_NAME"),
    verify_ssl_certs=False,
    profanity_check=False,
    timeout=300,
    top_p=0.1,
    temperature=0.1,
    max_tokens=500
)

tools = [get_all_cards, get_user_info, get_user_cards]

agent = create_react_agent(
    model=model,
    tools=tools,
    # подключение системного контекста
    state_modifier=system_prompt,
    # объект для сохранения памяти агента
    checkpointer=MemorySaver()
)
