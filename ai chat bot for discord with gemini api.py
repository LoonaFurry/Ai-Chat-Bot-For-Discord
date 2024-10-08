import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
import logging
import google.generativeai as genai
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration - Use environment variables for security
DISCORD_BOT_TOKEN = ('your-token-here')
GEMINI_API_KEY = ('your-key-here')

if not DISCORD_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("DISCORD_BOT_TOKEN or GEMINI_API_KEY not set in environment variables")

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Default response if Gemini API fails
DEFAULT_RESPONSE = "Sorry, I couldn't answer this question."

# Determine the directory where the code is located
CODE_DIR = os.path.dirname(__file__)

# File to store chat history, located in the code's directory
HISTORY_FILE = os.path.join(CODE_DIR, 'chat_history.json')

# Load chat history from file
def load_chat_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as file:
                if os.stat(HISTORY_FILE).st_size == 0:
                    return {}
                return json.load(file)
        except json.JSONDecodeError:
            logging.error("JSON decode error: file might be corrupted")
            return {}
        except Exception as e:
            logging.error(f"Error loading chat history: {e}")
            return {}
    return {}

# Save chat history to file with UTF-8 encoding
def save_chat_history(chat_history):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as file:  # Specify UTF-8 encoding
            json.dump(chat_history, file, indent=4, ensure_ascii=False)  # Ensure ASCII characters are not escaped
    except Exception as e:
        logging.error(f"Error saving chat history: {e}")
        
# Initialize chat history
chat_history = load_chat_history()

bot = commands.Bot(command_prefix='!', intents=intents)

status_list = [
    discord.Game(name="LolbitFurry's Chat Bot"),
    discord.Activity(type=discord.ActivityType.playing, name="I'm Ready To Chat With Fluffy Buddies ^w^"),
    discord.Activity(type=discord.ActivityType.listening, name="Foxy Land"),
    discord.Activity(type=discord.ActivityType.watching, name="OwO What's This?"),
]

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user}')
    change_status.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = str(message.author.id)

    if user_id not in chat_history:
        chat_history[user_id] = []

    # Ensure chat_history[user_id] is a list of dictionaries
    if not isinstance(chat_history[user_id], list):
        chat_history[user_id] = []

    chat_history[user_id].append({
        'message': message.content,  # Emojis are included in the message content
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'user_name': str(message.author),
        'user_id': user_id,
        'bot_id': str(bot.user.id),
        'bot_name': str(bot.user.name)
    })
    save_chat_history(chat_history)

    if bot.user.mentioned_in(message):
        content = message.content
        mention = message.author.mention

        # Generate history text from the stored messages
        history_text = "\n".join(entry['message'] for entry in chat_history[user_id] if isinstance(entry, dict) and 'message' in entry)
        prompt = (
            f"You Are a Furry Young Fox And You're Lovely And Kind, Patient, Cute, Understanding. "
            f"Remember all previous chats. Here is the chat history:\n{history_text}\n"
            f"Respond to the following message from {mention}: {content}"
        )

        if content.strip():
            try:
                response = await ask_gemini(prompt)
                await message.channel.send(f"{mention} {response}")
            except Exception as e:
                logging.error(f"Error processing message: {e}")
                await message.channel.send(f"{mention} Bir hata oluştu. Lütfen daha sonra tekrar deneyin.")

async def ask_gemini(prompt):
    try:
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: model.generate_content(prompt))
        if response and hasattr(response, 'text'):
            return response.text
        else:
            logging.info("API response: %s", response)
            return DEFAULT_RESPONSE
    except Exception as e:
        logging.error("API exception: %s", e)
        return DEFAULT_RESPONSE

@tasks.loop(seconds=60)
async def change_status():
    await bot.change_presence(activity=status_list[change_status.current_loop % len(status_list)])

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
