# security.py

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import config

def restricted(func):
    """
    Decorador que restringe el uso de un handler a los usuarios autorizados.
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        print(f"Intento de acceso del usuario ID: {user_id}", flush=True) # Log para depuración
        
        if user_id not in config.AUTHORIZED_USER_IDS:
            print(f"Acceso DENEGADO para el usuario ID: {user_id}", flush=True)
            if update.message:
                await update.message.reply_text("Lo siento, no tienes permiso para usar este bot.")
            elif update.callback_query:
                await update.callback_query.answer("Acceso denegado.", show_alert=True)
            return

        return await func(update, context, *args, **kwargs)
    return wrapped