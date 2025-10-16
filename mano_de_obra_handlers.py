# mano_de_obra_handlers.py

import mano_de_obra_queries
import query_handlers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler
from telegram.constants import ParseMode
from datetime import datetime
import urllib.parse

# --- ¡CORRECCIÓN! Añadimos un nuevo estado para el reporte final ---
SELECT_WEEK, SELECT_WORKER, REPORT_DISPLAYED = range(3)

async def start_mo_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la consulta de mano de obra pidiendo la semana."""
    query = update.callback_query
    await query.answer()
    
    _, weeks = mano_de_obra_queries.get_mo_workers_and_weeks()
    if not weeks:
        await query.edit_message_text("No se han registrado semanas en Mano de Obra.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(w, callback_data=f"mo_week_{w}")] for w in weeks]
    keyboard.append([InlineKeyboardButton("⬅️ Volver al Menú", callback_data="main_menu")])
    await query.edit_message_text("Consulta de Mano de Obra:\n\n¿De qué semana quieres el reporte?", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_WEEK

async def ask_worker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pide el trabajador después de seleccionar la semana."""
    query = update.callback_query
    await query.answer()
    week_name = query.data.split('_', 2)[2]
    context.user_data['mo_week'] = week_name
    
    workers, _ = mano_de_obra_queries.get_mo_workers_and_weeks()
    if not workers:
        await query.edit_message_text("No se han registrado trabajadores.")
        return ConversationHandler.END
        
    keyboard = [[InlineKeyboardButton(w, callback_data=f"mo_worker_{w}")] for w in workers]
    keyboard.append([InlineKeyboardButton("⬅️ Volver al Menú", callback_data="main_menu")])
    await query.edit_message_text(f"Semana: *{week_name}*\n\n¿Para qué trabajador?", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_WORKER

async def generate_mo_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Genera y muestra el reporte de desglose de mano de obra, con opción a imprimir."""
    query = update.callback_query
    await query.answer()
    worker_name = query.data.split('_', 2)[2]
    week_name = context.user_data['mo_week']
    
    await query.edit_message_text(f"Generando reporte para *{worker_name}* en *{week_name}*...", parse_mode='Markdown')
    
    report_data = mano_de_obra_queries.get_work_details(worker_name, week_name)
    if not report_data or not report_data['details']:
        await query.edit_message_text(f"No se encontró desglose de trabajo para *{worker_name}* en *{week_name}*.", parse_mode='Markdown')
        # Damos un momento para leer y luego volvemos al menú
        await asyncio.sleep(3)
        return await query_handlers.start(update, context)

    report_telegram = f"📋 *Desglose: {worker_name}*\nSemana: *{week_name}*\n{'-'*35}\n"
    report_printer = f"Desglose de Trabajo\nTrabajador: {worker_name}\nSemana: {week_name}\n--------------------------------\n"

    for item in report_data['details']:
        concept = item.get('CONCEPTO', 'N/A')
        quantity = float(item.get('CANTIDAD', 0.0) or 0.0)
        price = float(item.get('PRECIO', 0.0) or 0.0)
        amount = float(item.get('IMPORTE', 0.0) or 0.0)
        report_telegram += f"*{concept}*\n  `{quantity}` x `${price:,.2f}` = `${amount:,.2f}`\n"
        report_printer += f"{concept}\n  {quantity} x ${price:,.2f} = ${amount:,.2f}\n"

    report_telegram += f"\n💰 *Total Semana: ${report_data['total']:,.2f}*"
    report_printer += f"\nTotal Semana: ${report_data['total']:,.2f}"
    
    encoded_report = urllib.parse.quote(report_printer)
    print_url = f"https://webapp.dommsoluciones.com/print.html?data={encoded_report}"
    
    keyboard = [
        [InlineKeyboardButton("🖨️ Imprimir Reporte", web_app=WebAppInfo(url=print_url))],
        [InlineKeyboardButton("⬅️ Volver al Menú", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(report_telegram, parse_mode='Markdown', reply_markup=reply_markup)
    
    # --- ¡CORRECCIÓN! ---
    # En lugar de terminar, pasamos al estado de espera.
    return REPORT_DISPLAYED

# --- CONVERSATION HANDLER DE MANO DE OBRA (SIMPLIFICADO Y CORREGIDO) ---
mano_de_obra_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_mo_query, pattern="^start_mo$")
    ],
    states={
        SELECT_WEEK: [CallbackQueryHandler(ask_worker, pattern="^mo_week_")],
        SELECT_WORKER: [CallbackQueryHandler(generate_mo_report, pattern="^mo_worker_")],
        # --- ¡CORRECCIÓN! ---
        # Añadimos el nuevo estado que solo espera el botón para volver al menú.
        REPORT_DISPLAYED: [
            CallbackQueryHandler(query_handlers.start, pattern="^main_menu$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(query_handlers.start, pattern="^main_menu$"),
        CommandHandler("start", query_handlers.start)
    ],
)

