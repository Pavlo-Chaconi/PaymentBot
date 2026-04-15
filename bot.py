import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN, ALLOWED_USER_ID, PROXY_URL
from mail_client import check_mail_async

logging.basicConfig(level=logging.INFO)

import socket
import aiohttp
from aiogram.client.session.aiohttp import AiohttpSession

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан. Пожалуйста, создайте файл .env по примеру .env.example")

dp = Dispatcher()

async def periodic_mail_check(bot: Bot):
    """
    Фоновый процесс проверки почты.
    """
    # 12 часов = 12 * 60 * 60 = 43200 секунд
    check_interval = 43200 
    
    while True:
        # Сначала ждем, чтобы не спамить при старте, либо можно сразу вызвать
        await asyncio.sleep(check_interval)
        try:
            logging.info("Проверка почты по расписанию...")
            emails = await check_mail_async()
            
            if emails and ALLOWED_USER_ID:
                # В реальном приложении здесь нужно сохранять ID писем,
                # чтобы не отправлять одно и то же письмо дважды.
                # Пока что мы просто отправляем то, что найдено (макет).
                for email in emails:
                    msg_text = (
                        f"💸 <b>Новое уведомление об оплате</b>\n"
                        f"<b>От:</b> {email['from_']}\n"
                        f"<b>Тема:</b> {email['subject']}\n"
                        f"<b>Дата:</b> {email['date']}"
                    )
                    await bot.send_message(chat_id=ALLOWED_USER_ID, text=msg_text, parse_mode="HTML")
            
        except Exception as e:
            logging.error(f"Ошибка в periodic_mail_check: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if hasattr(message.from_user, "id") and message.from_user.id != ALLOWED_USER_ID:
         await message.answer("Извините, у вас нет доступа к этому боту.")
         return
         
    await message.answer(
        "Привет! Я бот для пересылки счетов на оплату из Яндекс.Почты.\n"
        "Я проверяю ящик каждые 12 часов.\n"
        "Для запуска немедленной проверки используй команду /check"
    )

@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    if message.from_user.id != ALLOWED_USER_ID:
         return
         
    await message.answer("Проверяю ящик...")
    emails = await check_mail_async()
    
    if not emails:
        await message.answer("Писем не найдено (или ящик пуст/ошибка конфигурации).")
        return
        
    for email in emails:
        msg_text = (
            f"💸 <b>Уведомление об оплате</b>\n"
            f"<b>От:</b> {email['from_']}\n"
            f"<b>Тема:</b> {email['subject']}"
        )
        try:
            await message.reply(msg_text, parse_mode="HTML")
        except Exception as e:
            await message.reply(f"Ошибка форматирования: {e}")

async def main():
    proxy = PROXY_URL or "socks5://127.0.0.1:1080"
    logging.info(f"Инициализация бота... Используем прокси: {proxy}")
    
    if proxy.startswith("socks"):
        # Если прокси SOCKS5 (xray). Добавляем rdns=True (аналог socks5h в curl), 
        # чтобы DNS расшифровывался на стороне Xray, а не на заблокированном сервере!
        from aiohttp_socks import ProxyConnector
        connector = ProxyConnector.from_url(proxy, family=socket.AF_INET, rdns=True)
        client_session = aiohttp.ClientSession(connector=connector)
        session = AiohttpSession()
        session._session = client_session
    elif proxy:
        # Если прокси обычный HTTP
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        client_session = aiohttp.ClientSession(connector=connector)
        session = AiohttpSession(proxy=proxy)
        session._session = client_session
    else:
        # Без прокси, но с IPv4
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        client_session = aiohttp.ClientSession(connector=connector)
        session = AiohttpSession()
        session._session = client_session
        
    bot = Bot(token=BOT_TOKEN, session=session)

    # Запускаем фоновую задачу проверки почты
    if ALLOWED_USER_ID:
        asyncio.create_task(periodic_mail_check(bot))
    else:
        logging.warning("ALLOWED_USER_ID не задан. Фоновая рассылка не запустится.")

    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
