import datetime
import logging
import os
import discord

from dotenv import load_dotenv
from discord.ext import commands


date = f'{datetime.datetime.now().year}-{datetime.datetime.now().month}-{datetime.datetime.now().day}'
os.makedirs("logs", exist_ok=True)
os.makedirs("configs", exist_ok=True)
logging.basicConfig(
    filename=f'logs/{date}.log',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True



bot = commands.Bot(
    command_prefix=['wolf.', 'Wolf.'],
    intents=intents,
    description='The MLN Network Bot\n\nFor support, feel free to join the MantiBot Support server and select the '
                'MLN Network role!\nhttps://discord.gg/SfPQV267u4',
    case_insensitive=True,
    owner_id=223980930975399937
)
@bot.event
async def on_ready():
    logging.info('Logged in as:')
    logging.info(bot.user.name)
    logging.info(bot.user.id)

    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            c = filename[:-3]
            try:
                await bot.load_extension(f'cogs.{c}')
                logging.info(f'Loaded cog: {c}')
            except Exception as e:
                logging.info(f'******\nFailed to load cog: {c}')
                logging.info(f'{type(e).__name__} - {e}')


# Main
if __name__ == '__main__':
    load_dotenv()
    token = os.getenv("LE_EPIC_BOT_TOKEN")
    bot.run(token)
