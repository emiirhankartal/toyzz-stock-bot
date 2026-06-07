import os
import asyncio
import requests
from playwright.async_api import async_playwright


DEFAULT_PRODUCT_URLS = """
https://www.toyzzshop.com/fifa-world-cup-2026-cikartma-albumu?serial=104378
"""

PRODUCT_URLS = [
    url.strip()
    for url in os.getenv("PRODUCT_URLS", DEFAULT_PRODUCT_URLS).splitlines()
    if url.strip()
]

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


async def check_stock(product_url):
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
            await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(10000)

            body_text = await page.locator("body").inner_text()
            print("Sayfa yazı uzunluğu:", len(body_text))

            if len(body_text.strip()) < 100:
                print("Sayfa düzgün okunamadı.")
                return "unknown"

            matched_buttons = await page.locator("button").evaluate_all("""
                buttons => {
                    function getButtonText(button) {
                        return [
                            button.innerText,
                            button.textContent,
                            button.getAttribute("aria-label"),
                            button.getAttribute("title"),
                            button.getAttribute("name")
                        ].join(" ").toLocaleLowerCase("tr-TR");
                    }

                    return buttons
                        .filter(button => {
                            const text = getButtonText(button);
                            return text.includes("tükendi") && text.includes("haber ver");
                        })
                        .map(button => {
                            return {
                                text: button.innerText || button.textContent || button.getAttribute("aria-label") || "",
                                disabled: button.disabled,
                                className: button.className
                            };
                        });
                }
            """)

            print("Tükendi/Haber Ver butonu sayısı:", len(matched_buttons))

            if len(matched_buttons) > 0:
                print("Bulunan buton:", matched_buttons[0]["text"])
                return "out_of_stock"

            return "in_stock"

        finally:
            await browser.close()


async def main():
    print("Kontrol edilecek ürün sayısı:", len(PRODUCT_URLS))

    for product_url in PRODUCT_URLS:
        print("--------------------------------")
        print("Ürün kontrol ediliyor:")
        print(product_url)

        status = await check_stock(product_url)
        print("Durum:", status)

        if status == "out_of_stock":
            print("Stok yok. Bildirim gönderilmedi.")

        elif status == "in_stock":
            send_telegram_message(
                "🔥 STOK GELMİŞ OLABİLİR!\n\n"
                f"{product_url}"
            )
            print("Telegram bildirimi gönderildi.")

        else:
            print("Stok durumu anlaşılamadı. Bildirim gönderilmedi.")


if __name__ == "__main__":
    asyncio.run(main())
