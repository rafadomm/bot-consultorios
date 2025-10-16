# dashboard_handler.py

import analytics_queries
import query_handlers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler
import json
import urllib.parse

# Estados para esta mini-conversación
SHOWING_DASHBOARD = 0

async def prepare_and_launch_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Calcula los datos y presenta el botón para abrir la Web App, iniciando una conversación.
    """
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Calculando analíticas, por favor espera... 🚁")

    dashboard_data = analytics_queries.get_full_analytics()

    json_data = json.dumps(dashboard_data)
    encoded_data = urllib.parse.quote(json_data)
    dashboard_url = f"https://webapp.dommsoluciones.com/dashboard.html?data={encoded_data}"

    keyboard = [
        [InlineKeyboardButton("🚀 Abrir Vista de Dron", web_app=WebAppInfo(url=dashboard_url))],
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data="main_menu")]
    ]
    await query.edit_message_text(
        "¡Listo! Tus datos están preparados. Presiona el botón para ver tu dashboard.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Entramos en el estado de espera para que el botón "Volver" funcione
    return SHOWING_DASHBOARD

# --- CONVERSATION HANDLER DEL DASHBOARD ---
dashboard_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(prepare_and_launch_dashboard, pattern="^prepare_dashboard$")
    ],
    states={
        SHOWING_DASHBOARD: [
            # En este estado, solo esperamos el botón para volver al menú
            CallbackQueryHandler(query_handlers.start, pattern="^main_menu$")
        ]
    },
    fallbacks=[
        # Si el usuario usa /start, también se sale
        CommandHandler("start", query_handlers.start)
    ],
    # Si el usuario no hace nada en 10 minutos, la conversación termina
    conversation_timeout=600
)