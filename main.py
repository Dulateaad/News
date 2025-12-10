import telebot
import os
import requests
from google import genai
from google.genai.errors import APIError

# --- КОНФИГУРАЦИЯ ---
# Токен вашего Telegram-бота, полученный от @BotFather
BOT_TOKEN = "8165044154:AAEgYURbqHBTZ3n-gEr9RT9ShqdC97r8Y84" 
# Ваш ключ Gemini API
GEMINI_API_KEY = "8170404283:AAErQO3ZFDmocJlgXZhSVV5qf8OvVUuNBZ4" 

# URL RSS-ленты TechCrunch для поиска свежих статей
RSS_FEED_URL = 'https://techcrunch.com/feed/'

# Инициализация клиента Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_client = genai.Client()
    GEMINI_MODEL = 'gemini-2.5-flash'
except Exception as e:
    print(f"Ошибка инициализации Gemini: {e}")
    gemini_client = None

# Инициализация Telegram-бота
bot = telebot.TeleBot(BOT_TOKEN)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def fetch_latest_article():
    """Получает заголовок, ссылку и текст последней статьи из RSS-ленты TechCrunch."""
    try:
        response = requests.get(RSS_FEED_URL)
        response.raise_for_status()
        
        # Простая и быстрая парсинг XML-ответа (только для примера)
        # В рабочем проекте лучше использовать библиотеку вроде feedparser
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        # Находим первый элемент <item>
        item = root.find('.//item')
        if item is None:
            return None, None, None

        title = item.find('title').text
        link = item.find('link').text
        # В RSS поле 'description' часто содержит HTML, но мы возьмем его для суммаризации
        description = item.find('description').text
        
        return title, link, description

    except Exception as e:
        print(f"Ошибка получения статьи из RSS: {e}")
        return None, None, None

def generate_summary(article_title, article_link, article_text):
    """Использует Gemini для суммаризации статьи в формат поста для Threads/Telegram."""
    if not gemini_client:
        return "Ошибка: Клиент Gemini не инициализирован."

    prompt = f"""
    Ты — профессиональный редактор новостей для Telegram. Твоя задача — создать идеальный новостной пост, основанный на предоставленной статье.
    
    1. **Суммаризируй** статью. Сохраняй профессиональный, но легкий тон.
    2. **Строго не превышай 450 символов** для всего текста (без учета ссылки).
    3. Добавь **3-4 релевантных хештега** в конце.
    4. Добавь **1-2 уместных эмодзи** в начале или середине.
    5. **Обязательно** используй Markdown для выделения ключевых моментов.
    6. В самом конце поста, на новой строке, **обязательно** укажи ссылку на полную статью.
    
    --- ЗАГОЛОВОК СТАТЬИ ---
    {article_title}
    
    --- ТЕКСТ СТАТЬИ ---
    {article_text}
    
    --- ССЫЛКА ---
    {article_link}
    """
    
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return response.text
    
    except APIError as e:
        return f"Ошибка API Gemini: {e}"
    except Exception as e:
        return f"Неизвестная ошибка при генерации: {e}"

# --- ОБРАБОТЧИКИ КОМАНД TELEGRAM ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Обрабатывает команды /start и /help."""
    welcome_text = (
        "🤖 Привет! Я бот-генератор новостей. "
        "Я могу взять последнюю статью с TechCrunch, "
        "используя Gemini, и превратить ее в короткий пост.\n\n"
        "Используй команду: /news"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['news'])
def handle_news_request(message):
    """Обрабатывает команду /news: получает статью и генерирует пост."""
    chat_id = message.chat.id
    bot.send_message(chat_id, "⏳ Ищу самую свежую статью и вызываю Gemini... Пожалуйста, подождите.")
    
    # 1. Получение статьи
    title, link, text = fetch_latest_article()
    
    if not title:
        bot.send_message(chat_id, "❌ Не удалось найти свежую статью. Попробуйте позже.")
        return

    # 2. Генерация поста
    summary_post = generate_summary(title, link, text)
    
    # 3. Отправка результата
    try:
        # Отправляем с режимом Markdown, чтобы сохранить форматирование от Gemini
        bot.send_message(chat_id, summary_post, parse_mode='Markdown')
    except telebot.apihelper.ApiTelegramException as e:
        # Если форматирование не удалось, отправляем как простой текст
        print(f"Ошибка Markdown: {e}. Отправка в виде простого текста.")
        bot.send_message(chat_id, summary_post)


# --- ЗАПУСК БОТА ---

print("Бот запущен. Ожидание сообщений...")
bot.polling()
