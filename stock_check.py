import os
import asyncio
import requests
from playwright.async_api import async_playwright


PRODUCT_URL = os.getenv(
    "PRODUCT_URL",
    "https://www.toyzzshop.com/fifa-world-cup-2026-adrenalyn-xl-trading-card-8li-paket?serial=102828"
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise Exception("Telegram token veya chat id eksik.")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    response = requests.post(url, data=data, timeout=20)
    response.raise_for_status()


async def check_stock():
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
            await page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)

            # Toyzz sayfası JavaScript ile yüklendiği için bekliyoruz.
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
    print("Ürün kontrol ediliyor...")
    print("URL:", PRODUCT_URL)

    status = await check_stock()
    print("Durum:", status)

    if status == "out_of_stock":
        print("Stok yok. Bildirim gönderilmedi.")

    elif status == "in_stock":
        send_telegram_message(
            "🔥 STOK GELMİŞ OLABİLİR!\n\n"
            "Toyzz Shop - FIFA World Cup 2026 Çıkartma Albümü\n"
            f"{PRODUCT_URL}"
        )
        print("Telegram bildirimi gönderildi.")

    else:
        print("Stok durumu anlaşılamadı. Yanlış alarm vermemek için bildirim gönderilmedi.")


if __name__ == "__main__":
    asyncio.run(main())
