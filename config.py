import os

# Получаем переменные окружения для продакшена
BOT_TOKEN = os.getenv("BOT_TOKEN", "8208358216:AAHDXPI3Aabn3CKHxzJkpTBWkvx3a4wrIPY")
API_ID = int(os.getenv("API_ID", "23792760"))
API_HASH = os.getenv("API_HASH", "65b45b91df3979791ded57a958d17993")
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN", "ZsAnXoIhTaxGkdtKiAOixknBZaj7s6lcidPRW3VWOE7J82xWRpFIP_Q9NsXy2VE_")
