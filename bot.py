import os
import json
import logging
import random
from datetime import datetime, date
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token from environment variable
TOKEN = os.getenv("8125260501:AAFCCgtAIPTMp_ghvvcMFioGRi33QfVuvmg")

if not TOKEN:
    logger.error("No TELEGRAM_BOT_TOKEN found in environment variables!")
    exit(1)

# Data persistence file
USERS_FILE = "users.json"

# Max codes per user per day
MAX_CODES_PER_DAY = 3

# Admin Telegram user ID - Replace this with your own Telegram user ID
# You can find it by messaging @userinfobot or by printing update.effective_user.id after /start
ADMIN_ID = None  # <-- Replace None with integer Telegram user ID for admin authorization

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading users file: {e}")
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    except Exception as e:
        logger.error(f"Error saving users file: {e}")

def get_today_str():
    return date.today().isoformat()

def is_admin(user_id):
    return user_id == ADMIN_ID

def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_markdown_v2(
        fr'Hola {user.mention_markdown_v2()}\! Bienvenido al Bot de códigos 2FA\.' +
        "\n\nEnvía /status para ver tu estado.\n" +
        "Si aún no tienes activada la opción para recibir códigos, por favor envíame tu ID de Telegram aquí para que pueda activarte.\n" +
        "Contacta al administrador con tu ID para solicitar activación.\n" +
        "Comandos disponibles:\n/getcode - Obtener código 2FA (máximo 3 diarios)\n/status - Ver estado\n/help - Ver ayuda"
    )

def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Bot para obtención de códigos 2FA.\n\n"
        "Comandos de usuario:\n"
        "/start - Inicio\n"
        "/getcode - Obtener código de doble autenticación (máximo 3 diarios)\n"
        "/status - Ver estado de activación y uso\n"
        "/help - Mostrar esta ayuda\n\n"
        "Comandos de administrador (sólo para ADMIN):\n"
        "/activate_user <telegram_user_id> - Activar usuario\n"
        "/deactivate_user <telegram_user_id> - Desactivar usuario\n"
        "/list_users - Listar usuarios registrados"
    )

def status(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    users = load_users()
    today = get_today_str()

    if user_id not in users:
        update.message.reply_text(
            f"No estás registrado.\nPor favor, envía tu ID de Telegram al administrador para activarte.\n"
            f"Tu ID es: {user_id}"
        )
        return

    user_entry = users[user_id]
    activated = user_entry.get("activated", False)
    last_date = user_entry.get("last_request_date", None)
    codes_sent = user_entry.get("codes_sent_today", 0)
    if last_date != today:
        codes_sent = 0

    update.message.reply_text(
        f"Estado de usuario:\n"
        f"ID: {user_id}\n"
        f"Activado: {'Sí' if activated else 'No'}\n"
        f"Códigos usados hoy: {codes_sent} de {MAX_CODES_PER_DAY}"
    )

def getcode(update: Update, context: CallbackContext) -> None:
    user_id = str(update.effective_user.id)
    users = load_users()
    today = get_today_str()

    if user_id not in users:
        # Register user with default deactivated state
        users[user_id] = {"activated": False, "codes_sent_today": 0, "last_request_date": None}
        save_users(users)
        update.message.reply_text(
            f"No estás registrado aún.\nTu ID es: {user_id}\n"
            "Por favor, contacta al administrador con este ID para activar tu cuenta."
        )
        return

    user_entry = users[user_id]
    if not user_entry.get("activated", False):
        update.message.reply_text("Tu cuenta no está activada para recibir códigos. Contacta al administrador.")
        return

    last_date = user_entry.get("last_request_date")
    codes_sent = user_entry.get("codes_sent_today", 0)
    if last_date != today:
        # Reset daily count
        codes_sent = 0

    if codes_sent >= MAX_CODES_PER_DAY:
        update.message.reply_text("Has alcanzado el límite de 3 códigos diarios. Intenta mañana nuevamente.")
        return

    # Generate 6-digit code
    code = f"{random.randint(0, 999999):06d}"

    # Here you can integrate with your account or store/share the code as needed.
    # For demonstration, we just send the code.

    codes_sent += 1
    user_entry["codes_sent_today"] = codes_sent
    user_entry["last_request_date"] = today
    users[user_id] = user_entry
    save_users(users)

    update.message.reply_text(
        f"Tu código de doble autenticación es:\n\n{code}\n\n"
        f"Códigos usados hoy: {codes_sent} de {MAX_CODES_PER_DAY}\n"
        "Este código es válido solo para esta sesión."
    )

def activate_user(update: Update, context: CallbackContext) -> None:
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        update.message.reply_text("No tienes permisos para usar este comando.")
        return

    args = context.args
    if len(args) != 1:
        update.message.reply_text("Uso: /activate_user <telegram_user_id>")
        return

    target_id = args[0]

    users = load_users()
    user_entry = users.get(target_id, {"activated": False, "codes_sent_today": 0, "last_request_date": None})
    user_entry["activated"] = True
    users[target_id] = user_entry
    save_users(users)
    update.message.reply_text(f"Usuario {target_id} activado para recibir códigos.")

def deactivate_user(update: Update, context: CallbackContext) -> None:
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        update.message.reply_text("No tienes permisos para usar este comando.")
        return

    args = context.args
    if len(args) != 1:
        update.message.reply_text("Uso: /deactivate_user <telegram_user_id>")
        return

    target_id = args[0]

    users = load_users()
    if target_id not in users:
        update.message.reply_text(f"Usuario {target_id} no está registrado.")
        return

    user_entry = users[target_id]
    user_entry["activated"] = False
    users[target_id] = user_entry
    save_users(users)
    update.message.reply_text(f"Usuario {target_id} desactivado.")

def list_users(update: Update, context: CallbackContext) -> None:
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        update.message.reply_text("No tienes permisos para usar este comando.")
        return

    users = load_users()
    if not users:
        update.message.reply_text("No hay usuarios registrados.")
        return

    lines = []
    for uid, udata in users.items():
        lines.append(f"ID: {uid} - Activado: {'Sí' if udata.get('activated', False) else 'No'} - Códigos hoy: {udata.get('codes_sent_today',0)}")
    text = "\n".join(lines)
    update.message.reply_text(f"Usuarios registrados:\n{text}")

def unknown_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Comando no reconocido. Escribe /help para ver los comandos disponibles.")

def main():
    global ADMIN_ID
    # Set your Telegram user ID here for admin access.
    # Example: ADMIN_ID = 123456789
    # You must replace None with your own Telegram user ID for the bot to recognize you as admin.
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
    if ADMIN_ID == 0:
        logger.error("ADMIN_ID not set or zero. Set the ADMIN_ID environment variable to your Telegram user ID.")
        exit(1)

    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("getcode", getcode))

    dispatcher.add_handler(CommandHandler("activate_user", activate_user))
    dispatcher.add_handler(CommandHandler("deactivate_user", deactivate_user))
    dispatcher.add_handler(CommandHandler("list_users", list_users))

    dispatcher.add_handler(MessageHandler(Filters.command, unknown_command))

    logger.info("Bot started...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

