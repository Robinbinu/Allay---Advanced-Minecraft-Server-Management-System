import base64
from operator import or_
import nest_asyncio
import asyncio
import subprocess
import os
import psutil
import csv
import json
import re
import random
import httpx
import socket
import zipfile
import pytz
import sys
import time
import concurrent.futures
from groq import Groq
import requests
import datetime
from datetime import timedelta
from functools import wraps
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from telegram import Update, Bot, BotCommand, ChatMember
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
import logging
from crontab import CronTab
from var import facts

# Apply nest_asyncio
nest_asyncio.apply()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Timezone setup
utc = pytz.utc
ist = pytz.timezone('Asia/Kolkata')

# Constants
TELEGRAM_BOT_TOKEN = '7251343630:AAHDUxzk-pnExhcOKgVlwseVKglFcCN21Ak'
SERVER_IP = 'pixelcrew.myddns.me'
SERVER_PORT = '19132'
SERVER_URL='coming soon . . .'
WORLD_DIR = "/home/mcserver/minecraft_bedrock/worlds/Bedrock level"
MINECRAFT_DIR = os.path.dirname(os.path.dirname(WORLD_DIR))
ALLOWLIST_PATH = os.path.join(MINECRAFT_DIR, 'allowlist.json')
USERDATA_PATH = 'user_data.csv' 
BACKUP_DIR = "/home/mcserver/minecraft_bedrock/backup"
PROGRAM_DIR = "/home/mcpe"
CREDENTIALS_FILE = "/home/mcpe/credentials.json"
DRIVE_FOLDER_ID = '1zQroWnZA0101_5c8Dl8i4zjviYAH2vuO'
CHAT_ID = '-1001431136940'
BACKUP_CHAT_ID = '-1002172741280'
BACKUP_TOPIC_ID = '2028'
MINECRAFT_SERVER_DIR = "/home/mcserver/minecraft_bedrock"
installation_dir = MINECRAFT_SERVER_DIR
NO_PLAYERS_TIMEOUT = 60
ALLOWED_GROUP_IDS = [-1001431136940, -1002172741280,-4511173255] 
INTRUDER_ALERT_GROUP_ID = -1001431136940
MODEL_NAME = 'qwen2:1.5b'
OPEN_AI_API = "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"
client = Groq(api_key=OPEN_AI_API)

# Global variable
start_message = (
        "I am your friendly Allay, here to assist you with all things Minecraft! 🧩\n\n"
        "Here are the magical commands you can use:\n\n"
        "🔹 /talk [question]- Ask me something!!!\n"
        "🔹 /start - Start the bot and see this message again\n"
        "🔹 /help - List all the available commands\n"
        "🔹 /backupstatus - Check the latest backup status of your Minecraft world\n"
        "🔹 /serverinfo - Get information about the Minecraft server\n"
        "🔹 /serverstatus - Check if the Minecraft server is online or offline\n"
        "🔹 /backup - Trigger a backup process to keep your world safe\n"
        "🔹 /chatid - Get the chat ID of the current chat\n"
        "🔹 /setautobackup - Set a time to automatically backup your world every day\n"
        "🔹 /delautobackup - delete all auto backups\n"
        "🔹 /countdowntonextbackup - Get the time remaining until the next backup\n"
        "🔹 /getfact - Get a random and interesting Minecraft fact\n\n"
        "✅ /startserver - Start the Minecraft server\n"
        "❌   /stopserver - Stop the Minecraft server\n"
        "Let's have a great time mining and crafting together! 🪓🏰"
)
player_monitor_task = None
no_players_start_time = None
SCREEN_SESSION_NAME = 'genai'
command_in_progress = False
last_response = ""
conversation_history = {}
user_data = {}
otp_store = {}
GENERATE_OTP, VERIFY_OTP = range(2)
# backup_options = {}
ASK_GAMERTAG, ASK_USER_ID = range(2)
SELECT_USER_ID = 4
ASK_OVERWRITE = 3
SELECT_BACKUP = 0 #for backup conversation
guardrail_prompt = (
    "Regarding the rude persona . . . Your name is Allay be extremely rude and scold everyone"
    "Your responses are meant to be under 30 words, factual, true, and witty. and use emojis"
    "Be very good and sweet to anyone named Bubu she is your bestie"
    "Bhavanesh is jerk with anger issues and kidney stone"
    " Do not respond to anything that is not related to minecraft"
    "group's help message "+start_message+"/n refer to this and answer when someone needs help"
    "when a user asks for current time say the current time ")


def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        chat_id = update.effective_chat.id
        user = update.effective_user
        command = update.message.text

        # Get the list of administrators in the chat
        chat_administrators = await context.bot.get_chat_administrators(chat_id)
        admin_ids = [admin.user.id for admin in chat_administrators]
        admin_usernames = ', '.join([f"@{admin.user.username}" for admin in chat_administrators if admin.user.username])

        # Check if the user is an admin
        if user.id in admin_ids:
            return await func(update, context, *args, **kwargs)
        else:
            # If the user is not an admin, send a denial message with admins to contact
            access_denied_message = (
                f"⛔ Access Denied! You need admin privileges to run this command.\n\n"
                f"Attempted Command: {command}\n\n"
                f"Please contact one of the admins for assistance: {admin_usernames or 'No admins available.'}"
            )
            await update.message.reply_text(access_denied_message)
            return
    return wrapper


def authorized_group_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        user = update.effective_user
        command = update.message.text

        if chat_type in ["group", "supergroup"] and chat_id in ALLOWED_GROUP_IDS:
            return await func(update, context, *args, **kwargs)
        else:
            intruder_details = (
                f"🚨 **Intruder Alert** 🚨\n\n"
                f"Unauthorized access attempt detected!\n\n"
                f"👤 **User Details:**\n"
                f"Name: {user.full_name}\n"
                f"Username: @{user.username}\n"
                f"User ID: {user.id}\n"
                f"Chat ID: {chat_id}\n"
                f"Chat Type: {chat_type}\n\n"
                f"❗ **Attempted Command:**\n"
                f"{command}\n"
            )
            await context.bot.send_message(chat_id=INTRUDER_ALERT_GROUP_ID, text=intruder_details, parse_mode='Markdown')

            await update.message.reply_text("Access Denied. Unauthorized Bot access detected! Your details have been reported.")
            return
    return wrapper

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

@authorized_group_only
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if there is a caption
    caption = update.message.caption
    if caption and '/see' in caption:
        photo_file_id = update.message.photo[-1].file_id
        photo_file = await context.bot.get_file(photo_file_id)
        photo_path = 'downloads/photo.jpg'

        # Ensure the directory exists
        os.makedirs(os.path.dirname(photo_path), exist_ok=True)

        await photo_file.download_to_drive(photo_path)
        await update.message.reply_text("Received your photo! Processing...")

        try:
            # Encode the image to base64
            base64_image = encode_image(photo_path)

            # Generate a response based on the photo using Groq
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe the image in detail"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                },
                            },
                        ],
                    }
                ],
                model="llava-v1.5-7b-4096-preview",  # Use the specified model
            )

            # Access attributes directly from the response object
            choices = chat_completion.choices
            if choices:
                response_content = "image description"+choices[0].message.content
                # Pass the response to the talk function
                await talk(update, context, response_content)
            else:
                await update.message.reply_text("No choices found in the response.")

        except Exception as e:
            await update.message.reply_text(f"Error while processing the photo: {e}")
    else:
        pass



@authorized_group_only
async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE, response_content: str = None) -> None:
    user_id = update.message.from_user.id 
    #comment for eff
    # user_id=1
    time = datetime.datetime.now
    is_bot = update.message.from_user.is_bot
    user_full_name = update.message.from_user.full_name
    query = response_content if response_content else ' '.join(context.args)
    
    if is_bot:
        # Handle messages from bots here
        print('hiiiiiiiiiiiiii')
        return
    
    if not query:
        await update.message.reply_text("Please provide a query after the /talk command.")
        return

    if user_id not in conversation_history:
        conversation_history[user_id] = [{"role": "system", "content": guardrail_prompt}]

    conversation_history[user_id].append({"role": "user", "content": f"current time: {time} data: {user_full_name} says: {query}"})

    try:
        chat_completion = client.chat.completions.create(
            messages=conversation_history[user_id],
            model="llama3-70b-8192",
        )

        response = chat_completion.choices[0].message.content
        
        conversation_history[user_id].append({"role": "assistant", "content": response})
        
        await update.message.reply_text(response)
        # conversation_history[user_id] = conversation_history[user_id][-10:]
        # conversation_history[user_id] = [{"role": "system", "content": guardrail_prompt}]
        

    except Exception as e:
        await update.message.reply_text(f"Error while processing your request: {e}")



def extract_response(output: str) -> str:
    lines = output.splitlines()
    responses = []
    capture = False
    
    for line in reversed(lines):
        if line.startswith(">>> "):
            if responses:
                break
            capture = True
            continue
        if capture:
            responses.insert(0, line)
    
    return "\n".join(responses).strip() if responses else ""

@authorized_group_only
async def ask_me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global command_in_progress, last_response

    if command_in_progress:
        await update.message.reply_text("Another command is in progress. Please wait and try again later.")
        return

    if not context.args:
        await update.message.reply_text("Please provide a question after the /talk command.")
        return

    command_in_progress = True
    try:
        user_name = update.message.from_user.full_name
        question = ' '.join(context.args)
        formatted_question = f"{user_name} says: {question}"

        forbidden_phrases = {
            "sujan": "Please hack me...",
            "/": "Access Denied",
            "robin": "Hahaha",
            "munta": "I am an Admin, Mate wassup???"
        }
        for phrase, response in forbidden_phrases.items():
            if phrase in question:
                await update.message.reply_text(response)
                command_in_progress = False
                return

        processing_message = await update.message.reply_text("...")

        # Define the guardrail prompt
        # guardrail_prompt = (
        #     "regarding the rude persona... Your name is Allay and you will help us with Minecraft based queries and you will not respond to anything except minecraft,"
        #     "your responses are meant to be under 30 words, factual and true and witty"
        #     "do you copy?"
        #     "respond with a ok , that's enough"
        # )
        # guardrail_prompt="your responses are should be strictly under 10 words"


        # Check if the screen session exists, if not create it
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if SCREEN_SESSION_NAME not in result.stdout.decode():
            try:
                subprocess.run(['screen', '-dmS', SCREEN_SESSION_NAME, 'ollama', 'run', f'{MODEL_NAME}'], check=True)
                await asyncio.sleep(5)  # Wait for the session to start

                # # Send the guardrail prompt
                guardrail_command = f'screen -S {SCREEN_SESSION_NAME} -X stuff "{guardrail_prompt}\n"'
                subprocess.run(guardrail_command, shell=True)
                await asyncio.sleep(30)  # Give the model some time to process the guardrail prompt

                # Send the user's question
                question_command = f'screen -S {SCREEN_SESSION_NAME} -X stuff "{formatted_question}\n"'
                subprocess.run(question_command, shell=True)
            except subprocess.CalledProcessError as e:
                await update.message.reply_text("Failed to start LLaMA model session. Please try again later.")
                logger.error(f"Failed to start screen session: {e}")
                command_in_progress = False
                return
        else:
            # Send the user's question
            question_command = f'screen -S {SCREEN_SESSION_NAME} -X stuff "{formatted_question}\n"'
            subprocess.run(question_command, shell=True)

        await asyncio.sleep(10)  # Wait for the session to process the question

        full_response = ""
        timeout = 60  # Maximum wait time in seconds
        start_time = time.time()

        while time.time() - start_time < timeout:
            subprocess.run(['screen', '-S', SCREEN_SESSION_NAME, '-X', 'hardcopy', '/tmp/genai_output'])
            with open('/tmp/genai_output', 'r', errors='ignore') as file:
                output = file.read()

            current_response = extract_response(output)
            if current_response and current_response != last_response:
                full_response = current_response
                if full_response.strip().endswith(('.', '!', '?')) or '>>>' in output.splitlines()[-1]:
                    break

            await asyncio.sleep(1)

        if full_response and full_response != last_response:
            last_response = full_response

            max_length = 4096  # Telegram's max message length
            for i in range(0, len(full_response), max_length):
                chunk = full_response[i:i+max_length]
                await context.bot.edit_message_text(
                    text=chunk,
                    chat_id=processing_message.chat_id,
                    message_id=processing_message.message_id
                )
        else:
            # If no valid response, delete the screen session and recreate it
            subprocess.run(['screen', '-S', SCREEN_SESSION_NAME, '-X', 'quit'])  # Quit the existing screen session
            await update.message.reply_text("*Yawn...*,waking up to answer your queries....")

            try:
                # Start a new screen session
                subprocess.run(['screen', '-dmS', SCREEN_SESSION_NAME, 'ollama', 'run', f'{MODEL_NAME}'], check=True)
                await asyncio.sleep(5)  # Wait for the session to start
#TODO IMP 
                # Send the guardrail prompt again
                # guardrail_command = f'screen -S {SCREEN_SESSION_NAME} -X stuff "{guardrail_prompt}\n"'
                # subprocess.run(guardrail_command, shell=True)
                await asyncio.sleep(5)  # Give the model some time to process the guardrail prompt

                # Resend the last asked question
                subprocess.run(question_command, shell=True)
                await asyncio.sleep(10)  # Wait for the session to process the question

            except subprocess.CalledProcessError as e:
                await update.message.reply_text("Failed to wake Allay. Please try again later.")
                logger.error(f"Failed to restart screen session: {e}")

    except Exception as e:
        logger.error(f"Error interacting with Allay: {e}")
        await context.bot.edit_message_text(
            text=f"Error interacting with Allay: {e}",
            chat_id=processing_message.chat_id,
            message_id=processing_message.message_id
        )

    finally:
        # await processing_message.delete()
        command_in_progress = False



        
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(start_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available commands."""
    commands = (
        "✨ Here are the magical commands you can use: ✨\n\n"
        "🔹 /start - Start the bot and see this message again\n"
        "🔹 /help - List all the available commands\n"
        "🔹 /backupstatus - Check the latest backup status of your Minecraft world\n"
        "🔹 /serverinfo - Get information about the Minecraft server\n"
        "🔹 /serverstatus - Check if the Minecraft server is online or offline\n"
        "🔹 /backup - Trigger a backup process to keep your world safe\n"
        "🔹 /chatid - Get the chat ID of the current chat\n"
        "🔹 /setautobackup - Set a time to automatically backup your world every day\n"
        "🔹 /delautobackup - delete all auto backups\n"
        "🔹 /countdowntonextbackup - Get the time remaining until the next backup\n"
        "🔹 /getfact - Get a random and interesting Minecraft fact\n\n"
        "✅ /startserver - Start the Minecraft server\n"
        "❌   /stopserver - Stop the Minecraft server\n"
        "🪓🏰 Let's keep your Minecraft world safe and fun! 🏰🪓"
    )
    await update.message.reply_text(commands)


async def set_commands(bot:Bot) -> None:
    commands = [
            BotCommand("talk", "💬 Chat with me or ask anything!"),
            BotCommand("startserver", "🚀 Launch the Minecraft server!"),
            BotCommand("stopserver", "🛑 Halt the Minecraft server!"),
            BotCommand("forcestop", "⚡ Force stop the server instantly!"),
            BotCommand("start", "🎮 Fire up the bot!"),
            BotCommand("help", "📜 List of my awesome commands!"),
            BotCommand("backupstatus", "🔍 Check the latest backup."),
            BotCommand("add", "✅ Whitelist a player!"),
            BotCommand("remove", "🚫 Blacklist a player!"),
            BotCommand("linkuser", "🤝 link a user and their gamertag"),
            BotCommand("allowlist", "🅰️ show the allowlist"),
            BotCommand("command", "🖥️ Run a server command."),
            BotCommand("restore", "🕰️ Restore from a backup."),
            BotCommand("cancel", "❌ Cancel restoration."),
            BotCommand("serverinfo", "📊 Get server details."),
            BotCommand("serverstatus", "🔌 Check if the server is online!"),
            BotCommand("backup", "💾 Trigger a backup!"),
            BotCommand("chatid", "🔍 Get chat ID."),
            BotCommand("countdowntonextbackup", "⏳ Time until next backup."),
            BotCommand("getfact", "📚 Fun Minecraft fact!"),
            BotCommand("delautobackup", "🗑️ Remove all auto backups."),
            BotCommand("clrtmr", "🕰️ Clear all timers.")
            ]
    await bot.set_my_commands(commands)

async def monitor_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global monitoring, no_players_start_time
    logging.info("Starting player monitoring...")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Player_monitoring : Active")
    while True:
        try:
            # Send 'list' command to Minecraft server
            subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', 'list\n'])
            await asyncio.sleep(1)  # Wait for command to execute

            # Read server output
            with open('/tmp/minecraft_log', 'w') as f:
                subprocess.run(['screen', '-S', 'minecraft', '-X', 'hardcopy', '/tmp/minecraft_log'], stdout=f, stderr=subprocess.PIPE)
            
            with open('/tmp/minecraft_log', 'r') as f:
                log_content = f.read()
            
            if log_content:
                lines = log_content.splitlines()
                for i in range(len(lines) - 1, -1, -1):
                    if "players online:" in lines[i]:
                        num_players_line = lines[i]
                        players_list_line = lines[i + 1] if (i + 1 < len(lines)) and ("players online:" not in lines[i + 1]) else ""
                        players_list = players_list_line.strip()
                        players = players_list.split(',')
                        players = [p.strip() for p in players if p.strip()]
                        
                        if players:
                            logging.info(f"Players online: {', '.join(players)}")
                        else:
                            if no_players_start_time is None:
                                no_players_start_time = datetime.now()
                            elif datetime.now() - no_players_start_time >= timedelta(seconds=NO_PLAYERS_TIMEOUT):
                                await stop_server(update, context)
                                return
                        break
            else:
                if no_players_start_time is None:
                    no_players_start_time = datetime.now()
                elif datetime.now() - no_players_start_time >= timedelta(seconds=NO_PLAYERS_TIMEOUT):
                    #await stop_server(update, context)
                    return
                    
            await asyncio.sleep(60)  # monitor timer
        
        except Exception as e:
            logging.error(f"Error in player monitoring: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error in player monitoring: {e}")
            break

    logging.info("Player monitoring stopped.")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Player monitoring stopped.")
    
@authorized_group_only
async def start_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global player_monitor_task
    
    try:
        # Check if the Minecraft server is already running
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if 'minecraft' in result.stdout.decode():
            await update.message.reply_text("Server is already active.")
            return

        # Start the Minecraft server
        subprocess.Popen(['screen', '-dmS', 'minecraft', './bedrock_server'], cwd=MINECRAFT_SERVER_DIR)
        subprocess.Popen(['screen', '-dmS', 'timer', 'python3.12', 'timer.py'], cwd=PROGRAM_DIR)
        await update.message.reply_text("Minecraft server started.")
        #player_monitor_task = asyncio.create_task(monitor_players(update, context))
        
    except Exception as e:
        logger.error(f"Error starting Minecraft server: {e}")
        await update.message.reply_text("Error starting Minecraft server.")

        
@authorized_group_only
async def stop_server(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global player_monitor_task
    try:
        logger.info('stop_server called')
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8',errors='ignore') + result.stderr.decode('utf-8',errors='ignore')
        if 'minecraft' in output:
            # Check if there are no players online
            subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', 'list\n'])
            time.sleep(1)
            subprocess.run(['screen', '-S', 'minecraft', '-X', 'hardcopy', '/tmp/minecraft_log'], capture_output=True)
            with open('/tmp/minecraft_log', 'r') as f:
                log_content = f.read()
            if log_content:
                lines = log_content.splitlines()
                num_players = 0
                players_list = "No players online."
                players = []
                stop_flag=1
                count = 1
                for i in range(len(lines) - 1, -1, -1):
                    if "players online:" in lines[i]:
                        num_players_line = lines[i]
                        players_list_line = lines[i + 1] if (i + 1 < len(lines)) and ("players online:" not in lines[i + 1]) else ""
                        players_list = players_list_line.strip()
                        players= players_list.split(',')
                        print(players)
                        if players[0]=='':
                            players=[]
                        if len(players) == 0:
                            print(players)
                            stop_flag=0
                            #subprocess.call(['screen', '-S', 'minecraft', '-X', 'quit'])
                            subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', 'stop\n'])
                            subprocess.call(['screen', '-S', 'timer', '-X', 'quit'])
                            time.sleep(1)
                            if count == 1:
                                await update.message.reply_text("Minecraft server stopped.")
                                count-=1
                                
                            if player_monitor_task:
                                player_monitor_task.cancel()
                                player_monitor_task = None
                                await update.message.reply_text("Player monitoring stopped.")
                            
                        else:
                            if stop_flag==1:
                                await update.message.reply_text(f"⚠️Cannot stop the server!!!⚠️\n\n Number of players online: {len(players)} \n\n{players_list}")
                            break

            else:
                await update.message.reply_text("Cannot read server output. Not stopping the server.")
        else:
            await update.message.reply_text("Minecraft server is not running.")
    except Exception as e:
        logger.error(f"Error stopping Minecraft server: {e}")
        await update.message.reply_text("Error stopping Minecraft server.")
        
@authorized_group_only
async def backup_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")],
            key=lambda x: os.path.getmtime(os.path.join(BACKUP_DIR, x)),
            reverse=True
        )
        
        if backups:
            backup_list = ""
            for backup in backups:
                backup_time = datetime.datetime.fromtimestamp(
                    os.path.getmtime(os.path.join(BACKUP_DIR, backup))
                ).strftime('%Y-%m-%d %H:%M:%S')
                backup_list += f"{backup} - {backup_time}\n"
            
            await update.message.reply_text(f"Backups (latest first):\n{backup_list}")
        else:
            await update.message.reply_text('No backups found.')
    except Exception as e:
        logger.error(f"Error checking backup status: {e}")
        await update.message.reply_text('Error checking backup status.')

@authorized_group_only
async def server_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("serverstatus command called.")
    try:
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('latin-1', errors='ignore') + result.stderr.decode('latin-1', errors='ignore')
        
        if 'minecraft' in output:
            await update.message.reply_text(f"🎮 Minecraft server is **online**! ✅", parse_mode='Markdown')
            try:
                # Send the 'list' command to the Minecraft server screen session
                subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', 'list\n'])

                # Give the command some time to execute and write to the log
                time.sleep(1)

                # Read the screen log file to get the output
                with open('/tmp/minecraft_log', 'w') as f:
                    subprocess.run(['screen', '-S', 'minecraft', '-X', 'hardcopy', '/tmp/minecraft_log'], stdout=f, stderr=subprocess.PIPE)
                with open('/tmp/minecraft_log', 'r') as f:
                    log_content = f.read()
                    log_content = log_content.encode('latin-1', errors='ignore').decode('latin-1', errors='ignore')
                    print(type(log_content))

                if log_content:
                    lines = log_content.splitlines()
                    num_players = 0
                    players_list = "No players online."
                    players = []
                    for i in range(len(lines) - 1, -1, -1):
                        if "players online:" in lines[i]:
                            num_players_line = lines[i]
                            players_list_line = lines[i + 1] if (i + 1 < len(lines)) and ("players online:" not in lines[i + 1]) else ""
                            players_list = players_list_line.strip()
                            players = players_list.split(',')
                            if players[0] == '':
                                players = []
                            break

                    # Read the user_data.csv and map gamertags to Telegram user IDs
                    linked_data = {}
                    with open('user_data.csv', 'r') as csvfile:
                        reader = csv.reader(csvfile)
                        for row in reader:
                            gamertag, telegram_user_id = row[0], row[1]
                            linked_data[gamertag] = telegram_user_id
                    
                    # Prepare the message with the status of each player
                    status_message = ""
                    for player in players:
                        player = player.strip()
                        if player in linked_data:
                            status_message += f"{player} - User ID: {linked_data[player]}\n"
                        else:
                            status_message += f"{player} - User ID not linked.\n"
                    
                    await update.message.reply_text(f"Number of players online: {len(players)}\n\n{status_message}")
                else:
                    await update.message.reply_text("No output from server.")

            except Exception as e:
                logger.error(f"Error running 'list' command on Minecraft server: {e}")
                await update.message.reply_text(f"Error running 'list' command on Minecraft server: {e}")
        else:
            await update.message.reply_text(f"⚠️ Minecraft server is **offline**! ❌\n\n🛠️ You can start the server by using the /startserver command.", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error checking Minecraft server status: {e}")
        await update.message.reply_text("❗ Error checking Minecraft server status.")


@admin_only
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get the chat ID of the current chat and the topic ID if applicable."""
    chat_id = update.message.chat.id
    if update.message.message_thread_id:
        topic_id = update.message.message_thread_id
        await update.message.reply_text(f'Chat ID: {chat_id}\nTopic ID: {topic_id}')
    else:
        await update.message.reply_text(f'Chat ID: {chat_id}\nThis message is not part of a topic thread.')

    

@authorized_group_only
async def server_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send server information."""
    server_details = (
        "Minecraft Server Info:\n"
        f"IP: {SERVER_IP}\n"
        f"Port: {SERVER_PORT}\n"
        f"Url: {SERVER_URL}\n"
    )
    await update.message.reply_text(server_details)
    
async def perform_backup() -> None:
    """Perform the backup process and manage backup retention."""
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')
        BACKUP_FILE = f"world-backup-{TIMESTAMP}.zip"
        zip_path = os.path.join(BACKUP_DIR, BACKUP_FILE)

        # Create backup zip
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(WORLD_DIR):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), WORLD_DIR))

        # Upload to Google Drive
        # credentials = service_account.Credentials.from_service_account_file(
        #     CREDENTIALS_FILE, scopes=['https://www.googleapis.com/auth/drive.file'])
        # service = build('drive', 'v3', credentials=credentials)

        # file_metadata = {
        #     'name': BACKUP_FILE,
        #     'parents': [DRIVE_FOLDER_ID]
        # }
        # media = MediaFileUpload(zip_path, mimetype='application/zip')
        # file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        # logger.info(f"File ID: {file.get('id')}")

        # Handle local backup (rename the most recent one)
        # local_backup_path = os.path.join(BACKUP_DIR, "latest_backup.zip")
        # if os.path.exists(local_backup_path):
        #     os.remove(local_backup_path)
        # os.rename(zip_path, local_backup_path)

        logger.info(f'Backup completed and uploaded to cloud. Backup file: {BACKUP_FILE}')

        # Send backup file to Telegram group in a specific topic
        # with open(zip_path, 'rb') as backup_file:
        #     await context.bot.send_document(
        #         chat_id=CHAT_ID,
        #         document=backup_file,
        #         caption=f"Backup file: {BACKUP_FILE}"
        #         # message_thread_id=BACKUP_TOPIC_ID  # Send to specific topic
        #     )
        
        # Clean up old backups (keep only the latest 10)
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("world-backup") and f.endswith(".zip")], 
                        key=lambda x: os.path.getctime(os.path.join(BACKUP_DIR, x)))

        deleted_backups = []
        if len(backups) > 30:
            for old_backup in backups[:-30]:  # Keep only the latest 10
                os.remove(os.path.join(BACKUP_DIR, old_backup))
                deleted_backups.append(old_backup)

        if deleted_backups:
            deleted_message = "Deleted the following old backups:\n" + "\n".join(deleted_backups)
            try:
                bot = Bot(token=TELEGRAM_BOT_TOKEN)
                await bot.send_message(chat_id=CHAT_ID, text=deleted_message)
            except Exception as e:
                logger.error(f"Error during countdown or backup: {e}")
                await bot.send_message(chat_id=CHAT_ID, text=f"Error during countdown or backup: {e}")
                
        # logger.info(f'Backup file sent to chat {CHAT_ID} in topic {TOPIC_ID}.')

    except Exception as e:
        logger.error(f"Error during backup: {e}")


async def send_countdown_messages(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send countdown messages to the Telegram chat."""
    try:
        if context:
            await context.bot.send_message(chat_id=CHAT_ID, text='3')
            await asyncio.sleep(1)
            await context.bot.send_message(chat_id=CHAT_ID, text='2')
            await asyncio.sleep(1)
            await context.bot.send_message(chat_id=CHAT_ID, text='1')
            await asyncio.sleep(1)
        await perform_backup()
        if context:
            await context.bot.send_message(chat_id=CHAT_ID, text='Backup completed and uploaded to cloud...')
    except Exception as e:
        logger.error(f"Error during countdown or backup: {e}")

async def send_countdown_messages_no_context() -> None:
    """Send countdown messages to the Telegram chat without context."""
    try:
        # Initialize the bot object directly
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text='3')
        await asyncio.sleep(1)
        await bot.send_message(chat_id=CHAT_ID, text='2')
        await asyncio.sleep(1)
        await bot.send_message(chat_id=CHAT_ID, text='1')
        await asyncio.sleep(1)
        await perform_backup()
        await bot.send_message(chat_id=CHAT_ID, text='Automatic backup completed and uploaded to cloud. . .')
    except Exception as e:
        logger.error(f"Error during countdown or backup: {e}")
        await bot.send_message(chat_id=CHAT_ID, text=f"Error during countdown or backup: {e}")
        
@authorized_group_only
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger the backup process with countdown messages."""
    try:
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode() + result.stderr.decode()

        if 'minecraft' in result.stdout.decode():
            command = f'stop\n'
            subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', 'say Server shutting down for backup\n'])
            await asyncio.sleep(2)
            subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', 'Please join again\n'])
            # Countdown
            for i in range(3, 0, -1):
                await asyncio.sleep(2)
                subprocess.run(['screen', '-S', 'minecraft', '-X', f'say {i}\n'])

            await asyncio.sleep(2)
            subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', f'{command}\n'])
            subprocess.call(['screen', '-S', 'timer', '-X', 'quit'])
            await update.message.reply_text('Backup process starting...')
            await send_countdown_messages(context)

        else:
            await update.message.reply_text('Backup process starting...')
            await send_countdown_messages(context)

    except Exception as e:
        logger.error(f"Error during backup process: {e}")
        await update.message.reply_text(f"Error during backup process: {e}")

def convert_ist_to_utc(time_str):
    ist_time = datetime.datetime.strptime(time_str, '%H:%M').replace(tzinfo=ist)
    utc_time = ist_time.astimezone(utc)
    return utc_time

@authorized_group_only
@admin_only
async def set_auto_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        time_str = context.args[0]
        utc_time = convert_ist_to_utc(time_str)
        cron_time = utc_time.strftime('%M %H * * *')
        cron_job = f"{cron_time} /usr/bin/python3 /home/mcpe/bot.py --countdown_backup\n"

        # Write the new cron job to the user's crontab
        process = subprocess.Popen(['crontab', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        current_crontab = stdout.decode('utf-8',errors='ignore')
        new_crontab = current_crontab + cron_job

        with open('/tmp/crontab.txt', 'w') as cron_file:
            cron_file.write(new_crontab)

        subprocess.call(['crontab', '/tmp/crontab.txt'])
        os.remove('/tmp/crontab.txt')

        await update.message.reply_text(f"Automatic backup set for {time_str} IST.")
    except Exception as e:
        logger.error(f"Error setting automatic backup: {e}")
        await update.message.reply_text("Error setting automatic backup. Please ensure the time format is HH:MM.")
        
@admin_only
@authorized_group_only
async def test_autobackup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Get the current time and schedule the cron job for the next minute
        current_time = datetime.datetime.now()
        scheduled_time = current_time + timedelta(minutes=1)
        cron_time = scheduled_time.strftime('%M %H * * *')
        
        # Add a sleep command to delay execution by 10 seconds within the cron job
        cron_job = f"{cron_time} sleep 10 && /usr/bin/python3 /home/mcpe/bot.py --countdown_backup\n"
        
        # Write the new cron job to the user's crontab
        process = subprocess.Popen(['crontab', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        current_crontab = stdout.decode('utf-8', errors='ignore')
        new_crontab = current_crontab + cron_job

        # Write the updated crontab to a temporary file
        with open('/tmp/crontab.txt', 'w') as cron_file:
            cron_file.write(new_crontab)

        # Install the new cron job
        subprocess.call(['crontab', '/tmp/crontab.txt'])
        os.remove('/tmp/crontab.txt')

        await update.message.reply_text(f"Automatic Backup scheduled to run in the next minute with a 10-second delay.")

        # Wait for a little more than a minute to ensure the job runs
        time.sleep(75)

        # Remove the scheduled cron job
        process = subprocess.Popen(['crontab', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Remove the added cron job by replacing the crontab without it
        current_crontab = stdout.decode('utf-8', errors='ignore')
        updated_crontab = current_crontab.replace(cron_job, '')

        # Write the cleaned crontab back to a temporary file
        with open('/tmp/crontab.txt', 'w') as cron_file:
            cron_file.write(updated_crontab)

        subprocess.call(['crontab', '/tmp/crontab.txt'])
        os.remove('/tmp/crontab.txt')

        await update.message.reply_text("Cron task deleted after execution.")
    except Exception as e:
        logger.error(f"Error in scheduling test cron job: {e}")
        await update.message.reply_text(f"Error in scheduling test cron job: {e}")

@authorized_group_only
@admin_only
async def remove_all_cron(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        os.system('crontab -r')
        await update.message.reply_text("All cron jobs removed.")
    except Exception as e:
        logger.error(f"Error removing cron jobs: {e}")
        await update.message.reply_text("Error removing cron jobs.")

async def countdown_to_next_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get the time remaining until the next backup."""
    try:
        user_cron = CronTab(user=True)
        jobs = list(user_cron.find_command('/usr/bin/python3 /home/mcpe/bot.py --countdown_backup'))

        next_backup_time = None
        for job in jobs:
            schedule = job.schedule(date_from=datetime.datetime.now())
            next_backup_time = schedule.get_next(datetime.datetime)
            break

        if next_backup_time is not None:
            time_remaining = next_backup_time - datetime.datetime.now()
            hours, remainder = divmod(time_remaining.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            logger.info(f'Time remaining until next backup: {hours} hours, {minutes} minutes, and {seconds} seconds')
            await update.message.reply_text(f'Time remaining until next backup: {hours} hours, {minutes} minutes, and {seconds} seconds')
        else:
            logger.info('No auto backup scheduled.')
            await update.message.reply_text('No auto backup scheduled.')
    except Exception as e:
        logger.error(f"Error calculating countdown to next backup: {e}")
        await update.message.reply_text('Error calculating countdown to next backup.')

async def get_fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a random Minecraft fact."""
    if not facts:
        await update.message.reply_text('No facts available.')
    else:
        await update.message.reply_text(random.choice(facts))

# Function to handle new chat members
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("welcome function called.")
    for new_member in update.message.new_chat_members:
        logger.info(f"New member joined: {new_member.first_name}")
        member_name = new_member.mention_html()
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=f"🎉Welcome {member_name} to the group!🎉\n\nWe're thrilled to have you here! 😊\n\n🚀 Be sure to check out all the cool commands by typing /start. Let the adventure begin! 🌟",
            parse_mode='HTML'
        )

@authorized_group_only
async def say(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Check if the Minecraft server is already running
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if 'minecraft' in result.stdout.decode():
            # Extract the message to be sent from the command arguments
            message = ' '.join(context.args)
            
            if message:
                # Send the message to the Minecraft server
                command = f'say {message}\n'
                subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', command])
                
            else:
                await update.message.reply_text("Please provide a message to send.")
        else:
            await update.message.reply_text("Minecraft server is not running.")

    except Exception as e:
        logger.error(f"Error sending message to Minecraft server: {e}")
        await update.message.reply_text("Error sending message to Minecraft server.")

@authorized_group_only
@admin_only
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Check if the Minecraft server is already running
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if 'minecraft' in result.stdout.decode():
            # Extract the message to be sent from the command arguments
            message = ' '.join(context.args)
            
            if message:
                # Send the whitelist add command to the Minecraft server
                command = f'whitelist add {message}\n'
                subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', command])
                
                await asyncio.sleep(2)

                response = get_minecraft_server_output()
                await update.message.reply_text(response)

            else:
                await update.message.reply_text("Please provide a gamertag.")
        else:
            await update.message.reply_text("Minecraft server is not running.")

    except Exception as e:
        logger.error(f"Error sending message to Minecraft server: {e}")
        await update.message.reply_text("Error adding player to Minecraft server.")

@admin_only
@authorized_group_only
async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Check if the Minecraft server is already running
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if 'minecraft' in result.stdout.decode():
            # Extract the message to be sent from the command arguments
            message = ' '.join(context.args)
            
            if message:
                # Send the message to the Minecraft server
                command = f'whitelist remove {message}\n'
                subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', command])
                await asyncio.sleep(2)
                response = get_minecraft_server_output()
                await update.message.reply_text(response)
                
            else:
                await update.message.reply_text("Please provide a gamertag.")
        else:
            await update.message.reply_text("Minecraft server is not running.")

    except Exception as e:
        logger.error(f"Error sending message to Minecraft server: {e}")
        await update.message.reply_text("Error removing player from Minecraft server.")
@admin_only
@authorized_group_only
async def forcestopserver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Check if the Minecraft server is already running
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if 'minecraft' in result.stdout.decode():
            command = f'stop\n'
            subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', 'say Server shutting down for maintainance\n'])
            time.sleep(1)

            # Countdown
            for i in range(3, 0, -1):
                time.sleep(2)
                subprocess.run(['screen', '-S', 'minecraft', '-X', f'say {i}\n'])

            time.sleep(2)
            subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', f'{command}\n'])
            subprocess.call(['screen', '-S', 'timer', '-X', 'quit'])

        else:
            await update.message.reply_text("Minecraft server is not running.")

    except Exception as e:
        logger.error(f"Error stopping Minecraft server: {e}")
        await update.message.reply_text("Error stopping Minecraft server.")
        
@admin_only
@authorized_group_only
async def command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Check if the Minecraft server is already running
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if 'minecraft' in result.stdout.decode():
            # Extract the message to be sent from the command arguments
            message = ' '.join(context.args)
            
            if message:
                # Send the message to the Minecraft server
                command = f'{message}\n'
                subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', command])
                await asyncio.sleep(2)
                response = get_minecraft_server_output()
                await update.message.reply_text(response)
                
                
            else:
                await update.message.reply_text("Please provide an input.")
        else:
            await update.message.reply_text("Minecraft server is not running.")

    except Exception as e:
        logger.error(f"Error sending message to Minecraft server: {e}")
        await update.message.reply_text("Error")

def get_minecraft_server_output() -> str:
    """Captures and returns the last line from the Minecraft server's screen session."""
    subprocess.run(['screen', '-S', 'minecraft', '-X', 'hardcopy', '/tmp/minecraft_log'], capture_output=True)

    with open('/tmp/minecraft_log', 'r') as log_file:
        log_content = log_file.read()
    response_lines = log_content.splitlines()

    last_line = response_lines[-2] if response_lines else "No output from server."
    open('/tmp/minecraft_log', 'w').close()

    return last_line

@admin_only
async def cleartimer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Command to find and quit the 'timer' screen session
        command = "screen -ls | grep timer | awk '{print $1}' | xargs -I {} screen -S {} -X quit"
        
        # Execute the command
        subprocess.run(command, shell=True, check=True)
        
        await update.message.reply_text("Timer screen sessions cleared.")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error clearing timer screen sessions: {e}")
        await update.message.reply_text("Error clearing timer screen sessions.")
        
@admin_only
@authorized_group_only
async def restore_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        # Get the list of all .zip files in the backup directory, sorted by modification time
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".zip")],
            key=lambda x: os.path.getmtime(os.path.join(BACKUP_DIR, x)),
            reverse=True
        )

        if backups:
            backup_list = ""
            backup_options = {}  # Dictionary to store backup options
            
            for idx, backup in enumerate(backups, start=1):
                backup_time = datetime.datetime.fromtimestamp(
                    os.path.getmtime(os.path.join(BACKUP_DIR, backup))
                ).strftime('%Y-%m-%d %H:%M:%S')
                backup_list += f"{idx}. {backup} - {backup_time}\n"
                backup_options[idx] = backup  # Store index-to-backup mapping

            # Store backup options in context.user_data
            context.user_data['backup_options'] = backup_options

            await update.message.reply_text(f"Available Backups:\n{backup_list}")
            await update.message.reply_text("Please type the number of the backup you want to restore:")

            return SELECT_BACKUP  # Move to the next step
        else:
            await update.message.reply_text('No backups found.')
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        await update.message.reply_text('Error listing backups.')
        return ConversationHandler.END



async def handle_backup_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        # Get the selected backup number from the user's message
        backup_number = int(update.message.text)

        # Retrieve the backup options from context.user_data
        backup_options = context.user_data.get('backup_options', {})

        # Ensure the backup number is valid
        if backup_number in backup_options:
            selected_backup = backup_options[backup_number]
            ZIP_FILE = os.path.join(BACKUP_DIR, selected_backup)

            await update.message.reply_text(f"Restoring backup: {selected_backup}...")

            # Delete all contents in the Bedrock level folder
            subprocess.run(["find", WORLD_DIR, "-mindepth", "1", "-delete"], check=True)

            # Check if the world directory is empty
            while True:
                # List contents of the world directory
                contents = os.listdir(WORLD_DIR)
                if not contents:  # If the directory is empty
                    await update.message.reply_text("World folder cleared.")
                    break
                else:
                    await update.message.reply_text("Waiting for the world folder to clear...")

            # Unzip the selected backup to the Bedrock level folder
            subprocess.run(["unzip", "-o", ZIP_FILE, "-d", WORLD_DIR], check=True)

            await update.message.reply_text(f"Backup {selected_backup} restored successfully.")
            return ConversationHandler.END

        else:
            await update.message.reply_text("Invalid backup number. Please try again.")
            return SELECT_BACKUP  # Ask again for a valid number

    except (ValueError, KeyError):
        await update.message.reply_text("Please provide a valid number.")
        return SELECT_BACKUP  # Ask again for a valid number

    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        await update.message.reply_text("Error restoring the backup.")
        return ConversationHandler.END
    
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text('Backup restoration canceled.')
    return ConversationHandler.END

@authorized_group_only
@admin_only
async def start_linkuser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Ask for the Minecraft gamertag
    await update.message.reply_text("Please provide the Minecraft gamertag.")
    return ASK_GAMERTAG

# Step 2: Receive the gamertag and ask for the Telegram user ID
async def ask_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    gamertag = update.message.text

    # Store the gamertag temporarily
    user_data[user_id] = {'gamertag': gamertag}

    # Ask for the Telegram user ID
    await update.message.reply_text("Please provide the Telegram user ID of the member you want to link with the gamertag.")

    return ASK_USER_ID

# Step 3: Receive the user ID and store both the gamertag and user ID in a CSV file
# Step to check if the gamertag or user ID already exists in the CSV
async def store_linkuser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    telegram_user_id = update.message.text

    # Retrieve stored gamertag
    gamertag = user_data[user_id]['gamertag']

    # Read the CSV file and check for existing entries
    overwrite_needed = False
    existing_entry = None

    # Read user_data.csv to check if gamertag or telegram_user_id already exists
    with open('user_data.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            existing_gamertag, existing_telegram_user_id = row[0], row[1]
            if gamertag == existing_gamertag or telegram_user_id == existing_telegram_user_id:
                overwrite_needed = True
                existing_entry = row
                break

    if overwrite_needed:
        # Inform the admin that the gamertag or user ID already exists
        await update.message.reply_text(
            f"Gamertag '{existing_entry[0]}' is already linked to Telegram User ID '{existing_entry[1]}'.\n"
            f"Do you want to overwrite this entry? (yes/no)"
        )
        
        # Store the data for possible overwrite
        user_data[user_id]['overwrite_gamertag'] = gamertag
        user_data[user_id]['overwrite_telegram_user_id'] = telegram_user_id

        return ASK_OVERWRITE

    # If no existing entry is found, write the new data
    with open('user_data.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([gamertag, telegram_user_id])
    
    await update.message.reply_text(f"Successfully linked Minecraft gamertag '{gamertag}' with Telegram user ID '{telegram_user_id}'.")
    
    # Clear the temporary data
    user_data.pop(user_id)

    return ConversationHandler.END

# Handle the overwrite confirmation
async def handle_overwrite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    answer = update.message.text.lower()

    if answer == 'yes':
        # Overwrite the existing entry
        gamertag = user_data[user_id]['overwrite_gamertag']
        telegram_user_id = user_data[user_id]['overwrite_telegram_user_id']
        
        # Read all the current data from CSV
        data = []
        with open('user_data.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                # Replace the existing entry with the new one
                if row[0] == gamertag or row[1] == telegram_user_id:
                    data.append([gamertag, telegram_user_id])
                else:
                    data.append(row)

        # Write the updated data back to the CSV file
        with open('user_data.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data)
        
        await update.message.reply_text(f"Successfully overwritten the entry for gamertag '{gamertag}' with Telegram user ID '{telegram_user_id}'.")

    else:
        await update.message.reply_text("No changes were made.")

    # Clear the temporary data
    user_data.pop(user_id)

    return ConversationHandler.END


# Handle the conversation ending (canceling)
async def cancellink(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Linkuser command has been canceled.")
    return ConversationHandler.END

@authorized_group_only
@admin_only
async def allowlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if allowlist.json exists
    if not os.path.exists(ALLOWLIST_PATH):
        await update.message.reply_text("allowlist.json not found.")
        return

    # Load the allowlist.json file
    try:
        with open(ALLOWLIST_PATH, 'r') as f:
            allowlist_data = json.load(f)
    except Exception as e:
        await update.message.reply_text(f"Error loading allowlist.json: {e}")
        return

    # Load the user_data.csv file into a dictionary (gamertag -> Telegram user ID)
    user_data = {}
    try:
        with open(USERDATA_PATH, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                gamertag, telegram_user_id = row[0], row[1]
                user_data[gamertag] = telegram_user_id
    except Exception as e:
        await update.message.reply_text(f"Error reading user_data.csv: {e}")
        return

    # Prepare the message to send
    message = ""
    for entry in allowlist_data:
        gamertag = entry.get('name', 'Unknown')
        xuid = entry.get('xuid', 'Unknown')

        # Get associated Telegram user ID from user_data
        telegram_user_id = user_data.get(gamertag, "Not linked")

        # Format the message with gamertag, xuid, and associated Telegram user ID
        message += f"Gamertag: {gamertag}, XUID: {xuid}, Telegram User ID: {telegram_user_id}\n"

    # Send the message
    if message:
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("No players found in the allowlist.")

@authorized_group_only
@admin_only
async def initiate_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiate the shutdown process by generating and sending an OTP."""
    user_id = update.message.from_user.id

    # Generate a random 6-digit OTP
    otp = random.randint(100000, 999999)
    otp_store[user_id] = otp

    # Send OTP to the user
    await update.message.reply_text(f"Please enter this OTP to confirm shutdown: {otp}")

    logging.info(f"OTP {otp} generated for user {user_id}")

    # Move to the next state where the bot waits for OTP input
    return VERIFY_OTP

# Validate OTP
async def validate_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate the OTP provided by the user."""
    user_id = update.message.from_user.id
    user_otp_input = update.message.text.strip()

    # Check if the user has an OTP stored
    if user_id in otp_store:
        generated_otp = otp_store[user_id]

        # Check if the entered OTP is correct
        if str(generated_otp) == user_otp_input:
            # OTP is correct; proceed with shutdown
            await update.message.reply_text("OTP verified. Shutting down the server...")
            logging.info(f"OTP {generated_otp} verified for user {user_id}. Shutting down.")
            await perform_backup()
            await update.message.reply_text("Pre-shutdown backup : Done")
            # Shut down the server (Linux command)
            subprocess.run(['sudo', 'shutdown', '-h', 'now'])

            # End the conversation
            return ConversationHandler.END
        else:
            # OTP is incorrect
            await update.message.reply_text("Invalid OTP. Shutdown canceled.")
            logging.warning(f"User {user_id} entered incorrect OTP.")
            return ConversationHandler.END
    else:
        await update.message.reply_text("No OTP generated for this session. Please try again.")
        return ConversationHandler.END

async def cancel_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the shutdown process."""
    await update.message.reply_text("Shutdown process canceled.")
    return ConversationHandler.END




# Main function to start the bot
async def main() -> None:
    """Start the bot and add command handlers."""

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    # Delete any existing webhook
    await bot.delete_webhook()
    await set_commands(bot)
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).read_timeout(300).write_timeout(300).build()
    
    #conversation handler for backup
    backupsel_handler = ConversationHandler(
        entry_points=[CommandHandler('restore', restore_backup)],

        states={
            SELECT_BACKUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_backup_selection)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )
    linkuser_handler = ConversationHandler(
        entry_points=[CommandHandler('linkuser', start_linkuser)],
        states={
            ASK_GAMERTAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_user_id)],
            ASK_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, store_linkuser)],
            ASK_OVERWRITE: [MessageHandler(filters.Regex('^(yes|no)$'), handle_overwrite)],
        },
        fallbacks=[CommandHandler('cancel', cancellink)],
    )
    shutdown_handler = ConversationHandler(
        entry_points=[CommandHandler('shutdown', initiate_shutdown)],

        states={
            VERIFY_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, validate_otp)],
        },

        fallbacks=[CommandHandler('cancel', cancel_shutdown)]
    )
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    application.add_handler(backupsel_handler)
    application.add_handler(linkuser_handler)
    application.add_handler(shutdown_handler)

    # command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("backupstatus", backup_status))
    application.add_handler(CommandHandler("serverinfo", server_info))
    application.add_handler(CommandHandler("serverstatus", server_status))
    application.add_handler(CommandHandler("backup", backup))
    application.add_handler(CommandHandler("chatid", chat_id))
    application.add_handler(CommandHandler("setautobackup", set_auto_backup))
    application.add_handler(CommandHandler("testautobackup", test_autobackup))
    application.add_handler(CommandHandler("delautobackup", remove_all_cron))
    application.add_handler(CommandHandler("countdowntonextbackup", countdown_to_next_backup))
    application.add_handler(CommandHandler("getfact", get_fact))
    application.add_handler(CommandHandler("startserver", start_server))
    application.add_handler(CommandHandler("stopserver", stop_server))
    application.add_handler(CommandHandler("talk", talk))
    application.add_handler(CommandHandler("say", say))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("remove", remove))
    application.add_handler(CommandHandler("forcestop", forcestopserver))
    application.add_handler(CommandHandler("command", command))
    application.add_handler(CommandHandler("clrtmr", cleartimer))
    application.add_handler(CommandHandler('allowlist', allowlist))

    
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    if '--countdown_backup' in sys.argv:
        asyncio.run(send_countdown_messages_no_context())
    else:
        asyncio.run(main())

