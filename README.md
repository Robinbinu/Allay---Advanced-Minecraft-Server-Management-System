# Allay - Advanced Minecraft Server Management System

## Overview
Allay is an advanced, Python-based automation tool engineered to **monitor, manage, and optimize** Minecraft servers with minimal manual intervention. Featuring **real-time power monitoring, automated backup solutions, player activity tracking, and seamless Telegram bot integration**, Allay ensures that your server remains operational, secure, and accessible from any location.

## Key Features 🚀
- **Power & Connectivity Monitoring**: Continuously tracks server uptime and sends real-time alerts via Telegram.
- **Automated Backups**: Periodically saves world data and securely uploads backups to Google Drive.
- **Remote Server Control**: Execute server commands effortlessly via Telegram bot commands.
- **Intelligent Player Activity Monitoring**: Automatically suspends the server when no players are online, optimizing resource utilization.
- **Intrusion Detection System**: Monitors and alerts administrators regarding unauthorized player logins.
- **AI-Driven Chatbot**: Leverages OpenAI’s API for smart, interactive player responses.
- **Secure Cloud Integration**: Ensures backup data integrity through Google Drive synchronization.
- **Comprehensive Server Notifications**: Sends status updates and maintenance alerts directly to in-game chat and Telegram.

## System Requirements 🛠️
- Python **3.8+**
- `pip` for package management
- Google Drive API credentials for cloud storage
- Dependencies installation:
  ```sh
  pip install -r requirements.txt
  ```

## Installation Guide ⚙️
1. **Clone the Repository:**
    ```sh
    git clone https://github.com/Robinbinu/allay.git
    cd allay
    ```
2. **Install Dependencies:**
    ```sh
    pip install -r requirements.txt
    ```
3. **Configure Environment Variables:**
   Modify `power_monitor.py` and `bot.py` to include:
   - `TELEGRAM_BOT_TOKEN`
   - `CHAT_ID`
   - `CREDENTIALS_FILE`
   - `DRIVE_FOLDER_ID`
   - `SERVER_IP`
   - `SERVER_PORT`
   - `MODEL_NAME`
   - `OPEN_AI_API`

## Technical Overview 🖥️
Allay operates through a **Telegram bot interface**, enabling server administrators to manage operations remotely. Built on **`python-telegram-bot`**, it employs asynchronous command handling to ensure responsive and efficient interactions.

### Core Modules
- **`bot.py`** - Handles Telegram-based server commands.
- **`power_monitor.py`** - Continuously monitors server uptime and network status.
- **`backup.py`** - Automates world data backups and Google Drive synchronization.
- **`restore.py`** - Facilitates recovery from cloud-based backups.
- **`ai_chat.py`** - Integrates AI-powered conversational abilities for in-game chat.

### System Functions
#### Power & Connectivity Monitoring ⚡
- Regularly pings the server to verify uptime.
- Detects power outages and initiates emergency backups.
- Sends immediate alerts to administrators via Telegram.
- Notifies players of server status through in-game chat.

#### Backup & Restore System 💾
- Automatically schedules and executes world backups.
- Enables manual backups via `/backup` command.
- Uploads and organizes backup files in Google Drive.
- Supports one-click restoration of previous backups.

#### Security & Intrusion Detection 🛡️
- Tracks player logins and flags unauthorized access attempts.
- Sends automated security alerts to designated Telegram groups.
- Employs AI-based moderation tools for enhanced server safety.

### Operational Workflow 🚀
1. **Bot Initialization:**
   - Clears previous webhooks.
   - Registers Telegram command handlers.
   - Begins polling for real-time updates.

2. **Command Processing:**
   - Accepts user inputs and maps them to predefined server functions.
   - Implements conversational state tracking for complex commands.

3. **Backup Management:**
   - Detects power failures and triggers automatic backup creation.
   - Synchronizes backups with Google Drive.
   - Sends alerts about the backup status to server admins and players.

4. **Intruder Monitoring & AI Chat:**
   - Identifies unauthorized player logins and alerts administrators.
   - Provides AI-powered responses to player queries in real-time.

## Usage Instructions ▶️
1. **Launch Power Monitoring Service:**
    ```sh
    python power_monitor.py
    ```
2. **Start the Telegram Bot Interface:**
    ```sh
    python bot.py
    ```
3. **Available Telegram Commands:**
    - `/start` - Initialize the bot and receive a welcome message.
    - `/help` - Display available bot commands.
    - `/backupstatus` - Check the status of the latest backup.
    - `/serverinfo` - Retrieve server IP and uptime details.
    - `/serverstatus` - Verify server online/offline status.
    - `/backup` - Initiate a manual backup.
    - `/chatid` - Fetch the chat ID linked to the bot.
    - `/setautobackup` - Schedule daily automated backups.
    - `/delautobackup` - Cancel all scheduled backups.
    - `/countdowntonextbackup` - View remaining time until the next backup.
    - `/getfact` - Receive an interesting Minecraft fact.
    - `/startserver` - Remotely start the Minecraft server.
    - `/stopserver` - Remotely stop the server.
    - `/chat` - Engage with the AI-driven chatbot.
    - `/intruderalert` - Get real-time notifications for unauthorized players.

## Contribution Guidelines 🤝
We welcome community contributions to enhance Allay's capabilities. To contribute, fork the repository and submit a pull request with your improvements.

## License 📜
This project is licensed under the **MIT License**. Refer to the `LICENSE` file for further details.

---
🚀 *Simplified Minecraft server management with Allay – ensuring optimal performance, security, and automation!*

