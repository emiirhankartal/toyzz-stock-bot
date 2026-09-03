import os
import asyncio
import requests
from playwright.async_api import async_playwright


ISMEK_URL = "https://ismek.istanbul/portal/egitim_detay.aspx?BransCode=5907"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS = [
    chat_id.strip()
    for chat_id in os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
    if chat_id.strip()
]


def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        raise Exception("Telegram token veya chat id listesi eksik.")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    for chat_id in TELEGRAM_CHAT_IDS:
        data = {
            "chat_id": chat_id,
            "text": message
        }

        response = requests.post(url, data=data, timeout=20)
        response.raise_for_status()

        print(f"Telegram bildirimi gönderildi: {chat_id}")


async def check_salsa():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        page = await browser.new_page(
            locale="tr-TR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        try:
            await page.goto(
                ISMEK_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            await page.wait_for_timeout(5000)

            # Önce "Eğitimin Verildiği Tüm Merkezler" kısmına tıkla
            centers_button = page.get_by_text(
                "Eğitimin Verildiği Tüm Merkezler",
                exact=True
            )

            if await centers_button.count() == 0:
                print("Eğitimin Verildiği Tüm Merkezler butonu bulunamadı.")
                return "unknown"

            print("Merkezler sekmesi bulundu, tıklanıyor...")

            await centers_button.first.click()

            # Dinamik içeriğin yüklenmesini bekle
            await page.wait_for_timeout(5000)

            body_text = await page.locator("body").inner_text()

            print("Tıklama sonrası sayfa içeriği:")
            print(body_text)

            closed_text = "Bu programda şu anda başvuru alınmamaktadır"

            # Kapalıysa direkt çık
            if closed_text in body_text:
                print("Başvuru alınmıyor.")
                return "closed"

            # Tıklama sonrası açılan bölümde Hemen Başvur ara
            apply_buttons = page.get_by_text(
                "Hemen Başvur",
                exact=True
            )

            button_count = await apply_buttons.count()

            print("Hemen Başvur butonu sayısı:", button_count)

            if button_count > 0:
                return "open"

            return "unknown"

        except Exception as e:
            print("Hata oluştu:", e)
            return "unknown"

        finally:
            await browser.close()

async def main():
    print("İSMEK Salsa 1. Seviye kontrol ediliyor...")

    status = await check_salsa()

    print("Durum:", status)

    if status == "closed":
        print("Başvuru kapalı. Bildirim gönderilmedi.")

    elif status == "open":
        send_telegram_message(
            "🚨 İSMEK SALSA 1. SEVİYE AÇILDI!\n\n"
            "Planlanan Merkezler bölümünde Hemen Başvur butonu göründü.\n\n"
            f"{ISMEK_URL}"
        )

        print("Telegram bildirimi gönderildi.")

    else:
        print("Durum anlaşılamadı. Bildirim gönderilmedi.")


if __name__ == "__main__":
    asyncio.run(main())
