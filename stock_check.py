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

        response = requests.post(
            url,
            data=data,
            timeout=20
        )

        response.raise_for_status()

        print(f"Telegram bildirimi gönderildi: {chat_id}")


async def check_course():
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
            print("Sayfa açılıyor...")

            await page.goto(
                ISMEK_URL,
                wait_until="commit",
                timeout=120000
            )

            print("Sayfaya bağlantı kuruldu.")

            # Site yavaş olduğu için biraz bekle
            await page.wait_for_timeout(15000)

            body_text = await page.locator("body").inner_text(
                timeout=30000
            )

            print("İlk body uzunluğu:", len(body_text))

            if len(body_text.strip()) < 100:
                print("Sayfa düzgün yüklenmedi.")
                return "unknown"

            # Gerçek tab ID'si
            centers_tab = page.locator("#merkezler-tab")

            tab_count = await centers_tab.count()

            print("merkezler-tab sayısı:", tab_count)

            if tab_count == 0:
                print("#merkezler-tab bulunamadı.")
                return "unknown"

            print("#merkezler-tab bulundu.")

            # Playwright görünürlük kontrolüne takılmasın diye
            # doğrudan DOM üzerinden click çalıştırıyoruz
            await centers_tab.evaluate(
                "el => el.click()"
            )

            print("Merkezler sekmesine JS click gönderildi.")

            # Tıklama sonrası dinamik veriyi bekle
            await page.wait_for_timeout(10000)

            body_text = await page.locator("body").inner_text(
                timeout=30000
            )

            print(
                "Tıklama sonrası body uzunluğu:",
                len(body_text)
            )

            apply_count = body_text.count("Hemen Başvur")

            closed_text = (
                "Bu programda şu anda başvuru alınmamaktadır"
            )

            closed_found = closed_text in body_text

            print(
                "Hemen Başvur sayısı:",
                apply_count
            )

            print(
                "Başvuru alınmamaktadır yazısı var mı:",
                closed_found
            )

            # Öncelik açık başvuruda.
            # Sayfanın başka bir yerinde kapalı mesajı kalmış olsa bile
            # Hemen Başvur varsa bildirim gönder.
            if apply_count > 0:
                return "open"

            if closed_found:
                return "closed"

            print("Durum belirlenemedi.")

            print(
                "Tıklama sonrası ilk 10000 karakter:"
            )

            print(body_text[:10000])

            return "unknown"

        except Exception as e:
            print("HATA:")
            print(repr(e))

            return "unknown"

        finally:
            await browser.close()


async def main():

    print("İSMEK kursu kontrol ediliyor...")
    print(ISMEK_URL)

    status = await check_course()

    print("Durum:", status)

    if status == "closed":

        print(
            "Başvuru kapalı. "
            "Telegram bildirimi gönderilmedi."
        )

    elif status == "open":

        send_telegram_message(
            "🚨 İSMEK KURS BAŞVURUSU AÇIK!\n\n"
            "Aktif bir 'Hemen Başvur' seçeneği bulundu.\n\n"
            f"{ISMEK_URL}"
        )

        print(
            "Telegram bildirimi gönderildi."
        )

    else:

        print(
            "Durum anlaşılamadı. "
            "Telegram bildirimi gönderilmedi."
        )


if __name__ == "__main__":
    asyncio.run(main())
