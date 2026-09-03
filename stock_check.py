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

            print("Sayfaya bağlantı kuruldu, içerik bekleniyor...")

            await page.wait_for_timeout(15000)

            body_text = await page.locator("body").inner_text(
                timeout=30000
            )

            print("Body uzunluğu:", len(body_text))

            if len(body_text.strip()) < 100:
                print("Sayfa içeriği yeterli gelmedi.")
                return "unknown"

            centers = page.get_by_text(
                "Eğitimin Verildiği Tüm Merkezler",
                exact=True
            )

            count = await centers.count()

            print("Merkezler sekmesi sayısı:", count)

            if count == 0:
                print("Merkezler sekmesi bulunamadı.")
                print("İlk 5000 karakter:")
                print(body_text[:5000])
                return "unknown"

            clicked = False

            for i in range(count):
                try:
                    visible = await centers.nth(i).is_visible()

                    print(
                        f"Merkezler elemanı {i} görünür mü:",
                        visible
                    )

                    if visible:
                        print(
                            "Eğitimin Verildiği Tüm Merkezler "
                            "sekmesine tıklanıyor..."
                        )

                        await centers.nth(i).click(
                            force=True,
                            timeout=30000
                        )

                        clicked = True
                        break

                except Exception as e:
                    print(
                        f"Merkez elemanı {i} kontrol hatası:",
                        repr(e)
                    )

            if not clicked:
                print("Görünür merkez sekmesine tıklanamadı.")
                return "unknown"

            print("Sekmeye tıklandı, merkezler bekleniyor...")

            await page.wait_for_timeout(10000)

            body_text = await page.locator("body").inner_text(
                timeout=30000
            )

            print("Tıklama sonrası body uzunluğu:", len(body_text))

            closed_text = (
                "Bu programda şu anda başvuru alınmamaktadır"
            )

            closed_found = closed_text in body_text
            apply_count = body_text.count("Hemen Başvur")

            print("Başvuru kapalı yazısı var mı:", closed_found)
            print("Hemen Başvur sayısı:", apply_count)

            if closed_found:
                return "closed"

            if apply_count > 0:
                return "open"

            print("Ne açık ne kapalı durumu tespit edilebildi.")
            print("Tıklama sonrası ilk 10000 karakter:")
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
            "Planlanan merkezlerde aktif "
            "Hemen Başvur seçeneği bulundu.\n\n"
            f"{ISMEK_URL}"
        )

        print("Telegram bildirimi gönderildi.")

    else:
        print(
            "Durum anlaşılamadı. "
            "Telegram bildirimi gönderilmedi."
        )


if __name__ == "__main__":
    asyncio.run(main())
