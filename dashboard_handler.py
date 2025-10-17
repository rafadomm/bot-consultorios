# dashboard_handler.py

import analytics_queries, query_handlers
from security import restricted
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler
import json
import urllib.parse

# Estados
SHOWING_DASHBOARD = 0

async def prepare_and_launch_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    await query.edit_message_text("Calculando analíticas... 🚁")
    dashboard_data = analytics_queries.get_full_analytics()
    json_data = json.dumps(dashboard_data)
    encoded_data = urllib.parse.quote(json_data)
    dashboard_url = f"https://webapp.dommsoluciones.com/dashboard.html?data={encoded_data}"
    keyboard = [
        [InlineKeyboardButton("🚀 Abrir Vista de Dron", web_app=WebAppInfo(url=dashboard_url))],
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data="main_menu")]
    ]
    await query.edit_message_text("¡Listo! Presiona para ver tu dashboard.", reply_markup=InlineKeyboardMarkup(keyboard))
    return SHOWING_DASHBOARD

# --- CONVERSATION HANDLER (Al final del archivo y protegido) ---
dashboard_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(restricted(prepare_and_launch_dashboard), pattern="^prepare_dashboard$")],
    states={
        SHOWING_DASHBOARD: [
            CallbackQueryHandler(query_handlers.start, pattern="^main_menu$")
        ]
    },
    fallbacks=[CommandHandler("start", query_handlers.start)],
)