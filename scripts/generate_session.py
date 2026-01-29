from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

# Load env variables from root .env if exists
load_dotenv(".env")
load_dotenv(".env.production")

api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")

if not api_id or not api_hash:
    print("Error: TELEGRAM_API_ID or TELEGRAM_API_HASH not found in env.")
    api_id = input("Enter API ID: ")
    api_hash = input("Enter API HASH: ")

print("Logging in to generate String Session...")

with TelegramClient(StringSession(), int(api_id), api_hash) as client:
    print("\n=== YOUR STRING SESSION (COPY BELOW) ===\n")
    print(client.session.save())
    print("\n========================================\n")
    print("Add this string to Railway Environment Variables as TELETHON_SESSION")
