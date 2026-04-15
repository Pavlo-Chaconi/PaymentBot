from imap_tools import MailBox, AND
import asyncio
from config import YANDEX_EMAIL, YANDEX_PASSWORD

def fetch_payment_emails():
    """
    Синхронная функция для подключения к Яндексу и получения писем.
    Возвращает список словарей с информацией о письме.
    """
    if not YANDEX_EMAIL or not YANDEX_PASSWORD:
        return []

    found_emails = []
    
    server = 'imap.yandex.ru'
    try:
        with MailBox(server).login(YANDEX_EMAIL, YANDEX_PASSWORD) as mailbox:
            # Ищем ТОЛЬКО непрочитанные письма от бизнес-аккаунта Яндекса
            # По умолчанию метод fetch сделает эти письма прочитанными (mark_seen=True)
            for msg in mailbox.fetch(AND(seen=False, from_="business-info@360.yandex.ru")):
                found_emails.append({
                    "subject": msg.subject,
                    "from_": msg.from_,
                    "date": msg.date.strftime("%d.%m.%Y %H:%M"),
                    "text": msg.text[:200] # Берем только начало текста для превью
                })
    except Exception as e:
        print(f"Ошибка при подключении к почте: {e}")
        
    return found_emails

async def check_mail_async():
    """
    Асинхронная обертка для вызова синхронного кода imap_tools
    в отдельном потоке, чтобы не блокировать event loop бота.
    """
    return await asyncio.to_thread(fetch_payment_emails)
