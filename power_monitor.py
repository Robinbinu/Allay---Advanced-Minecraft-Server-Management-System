import subprocess
import time
import requests
import logging
import datetime
import os
import asyncio
import zipfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration
TARGET_IP = "192.168.0.5"  # Target IP to ping
PING_INTERVAL = 3  # Interval to check connectivity in seconds
TELEGRAM_BOT_TOKEN = '7251343630:AAHDUxzk-pnExhcOKgVlwseVKglFcCN21Ak'
TELEGRAM_CHAT_ID = '-1001431136940'

# Backup configuration
WORLD_DIR = "/home/mcserver/minecraft_bedrock/worlds/Bedrock level"
BACKUP_DIR = "/home/mcserver/minecraft_bedrock/backup"
CREDENTIALS_FILE = "/home/mcpe/credentials.json"
DRIVE_FOLDER_ID = '1KI0ykk8vUVzKyK4Ur6IlFwDlg_W_Ysx4'

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler('power_monitor.log')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        logger.info(f'Message sent to Telegram: {message}')
    except requests.RequestException as e:
        logger.error(f'Error sending message to Telegram: {e}')

def say_to_minecraft_server(message):
    try:
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if 'minecraft' in result.stdout.decode():
            command = f'say {message}\n'
            subprocess.run(['screen', '-S', 'minecraft', '-X', 'stuff', command])
            logger.info(f'Message sent to Minecraft server: {message}')
        else:
            logger.warning("Minecraft server is not running.")
    except Exception as e:
        logger.error(f"Error sending message to Minecraft server: {e}")

def check_internet():
    try:
        subprocess.check_output(["ping", "-c", "1", TARGET_IP], stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError:
        return False

async def perform_backup() -> None:
    """Perform the backup process."""
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        TIMESTAMP = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')
        BACKUP_FILE = f"world-backup-{TIMESTAMP}.zip"
        zip_path = os.path.join(BACKUP_DIR, BACKUP_FILE)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(WORLD_DIR):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), WORLD_DIR))

        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=['https://www.googleapis.com/auth/drive.file'])
        service = build('drive', 'v3', credentials=credentials)

        file_metadata = {
            'name': BACKUP_FILE,
            'parents': [DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(zip_path, mimetype='application/zip')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f"File ID: {file.get('id')}")

        local_backup_path = os.path.join(BACKUP_DIR, "latest_backup.zip")
        if os.path.exists(local_backup_path):
            os.remove(local_backup_path)
        os.rename(zip_path, local_backup_path)

        logger.info(f'Backup completed and uploaded to Google Drive. Backup file: {BACKUP_FILE}')
    except Exception as e:
        logger.error(f"Error during backup: {e}")

async def main():
    logger.info('Initiating power and connectivity monitoring...')
    was_connected = check_internet()
    logger.info(f'Initial connectivity status: {"Online" if was_connected else "Offline"}')

    downtime_start = None

    try:
        while True:
            time.sleep(PING_INTERVAL)
            is_connected = check_internet()

            if is_connected and not was_connected:
                if downtime_start:
                    downtime_duration = time.time() - downtime_start
                    downtime_minutes = int(downtime_duration // 60)
                    downtime_seconds = int(downtime_duration % 60)
                    message = (
                        f'🔌 Power Restored: The server is back online after a downtime of '
                        f'{downtime_minutes} minutes and {downtime_seconds} seconds. '
                        'Backups completed successfully. You can safely continue your gameplay.'
                    )
                    mmessage = (
                        f'Power Restored: The server is back online after a downtime of '
                        f'{downtime_minutes} minutes and {downtime_seconds} seconds. '
                        'Backups completed successfully. You can safely continue your gameplay.'
                    )
                    send_telegram_message(message)
                    say_to_minecraft_server(message)
                    downtime_start = None
            elif not is_connected and was_connected:
                downtime_start = time.time()
                message = (
                    '⚠️ Power Loss Detected: The server is experiencing a power issue. '
                    'Automatic backup sequence initiated.\n\n🚨 Attention Players: If you have made any recent progress, '
                    'please manually initiate a backup as soon as possible to ensure your data is safe.'
                )
                mmessage = (
                    'Power Loss Detected: The server is experiencing a power issue. '
                    'Automatic backup sequence initiated.\n\nAttention Players: If you have made any recent progress, '
                    'please manually initiate a backup as soon as possible to ensure your data is safe.'
                )
                send_telegram_message(message)
                say_to_minecraft_server(mmessage)
                await perform_backup()

            was_connected = is_connected
    except KeyboardInterrupt:
        logger.info('Script execution interrupted by user.')
        print("Script execution interrupted. Exiting gracefully...")

if __name__ == '__main__':
    asyncio.run(main())
