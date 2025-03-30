import time
import asyncio
import subprocess
import logging
from telegram import Update, Bot, BotCommand, ChatMember
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Bot

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
TELEGRAM_BOT_TOKEN = "7251343630:AAHDUxzk-pnExhcOKgVlwseVKglFcCN21Ak"
CHAT_ID = "-1001431136940"
duration = 300

async def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message)


async def run_timer():
    counter = 0
    last_players = set()
    while True:
        start_time = time.time()

        # Wait for 30 seconds
        while time.time() - start_time < duration:
            time_elapsed = time.time() - start_time
            print(f"\rTime elapsed: {time_elapsed:.2f} seconds", end="", flush=True)
            await asyncio.sleep(0.1)

        counter += 1
        print(f"\n{duration} second mark reached! (Count: {counter})")
        try:
            logger.info("monitor_server called")
            result = subprocess.run(
                ["screen", "-ls"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            output = result.stdout.decode("utf-8") + result.stderr.decode("utf-8")
            if "minecraft" in output:
                # Check if there are no players online
                subprocess.run(["screen", "-S", "minecraft", "-X", "stuff", "list\n"])
                time.sleep(1)
                subprocess.run(
                    ["screen", "-S", "minecraft", "-X", "hardcopy", "/tmp/minecraft_log"],
                    capture_output=True,
                )
                with open("/tmp/minecraft_log", "r") as f:
                    log_content = f.read()
                if log_content:
                    lines = log_content.splitlines()
                    num_players = 0
                    players_list = "No players online."
                    players = []
                    stop_flag = 1
                    count = 1
                    for i in range(len(lines) - 1, -1, -1):
                        if "players online:" in lines[i]:
                            num_players_line = lines[i]
                            players_list_line = (
                                lines[i + 1]
                                if (i + 1 < len(lines))
                                and ("players online:" not in lines[i + 1])
                                else ""
                            )
                            players_list = players_list_line.strip()
                            players = players_list.split(",")
                            print(players)
                            # current_players = set(players)

                            # # Check if a new player has joined
                            # new_players = current_players - last_players
                            # if new_players:
                            #     await send_telegram_message(
                            #         f"🎮 New player(s) joined the Minecraft server: {', '.join(new_players)}"
                            #     )
                            # last_players = current_players

                            if players[0] == "":
                                players = []
                            if len(players) == 0:
                                print(players)
                                stop_flag = 0
                                subprocess.run(
                                    ["screen", "-S", "minecraft", "-X", "stuff", "stop\n"]
                                )
                                time.sleep(1)
                                if count == 1:
                                    await send_telegram_message(
                                        f"🚨 Minecraft server stopped! No players detected for ⏳ {duration} seconds."
                                    )
                                    subprocess.call(['screen', '-S', 'timer', '-X', 'quit'])
                                    count -= 1
                            else:
                                break
                else:
                    print('ok')
            else:
                print('ok ok')
        except Exception as e:
            logger.error(f"Error stopping Minecraft server: {e}")
            


if __name__ == "__main__":
    print("Starting timer...")
    asyncio.run(run_timer())
