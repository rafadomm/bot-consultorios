# mano_de_obra_handlers.py

import mano_de_obra_queries
import query_handlers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler
from telegram.constants import ParseMode
from datetime import datetime

# Estados solo para esta conversación
SELECT_WORKER = 0

async def start_mo_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la consulta de pagos pidiendo un trabajador."""
    query = update.callback_query
    await query.answer()
    
    workers = mano_de_obra_queries.get_paid_workers()
    if not workers:
        await query.edit_message_text("No se han registrado pagos para ningún trabajador.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(w, callback_data=f"mo_worker_{w}")] for w in workers]
    keyboard.append([InlineKeyboardButton("⬅️ Volver al Menú", callback_data="main_menu")])
    await query.edit_message_text("Consulta de Pagos: ¿De qué trabajador quieres ver el reporte?", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_WORKER

async def generate_payment_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Genera y muestra el reporte de pagos para el trabajador seleccionado."""
    query = update.callback_query
    await query.answer()
    worker_name = query.data.split('_', 2)[2]
    
    await query.edit_message_text(f"Generando reporte para *{worker_name}*...", parse_mode='Markdown')
    
    payments = mano_de_obra_queries.get_payments_by_worker(worker_name)
    if not payments:
        await query.edit_message_text(f"No se encontraron pagos para *{worker_name}*.", parse_mode='Markdown')
        return ConversationHandler.END

    # Agrupamos los pagos por semana
    payments_by_week = {}
    for payment in payments:
        week = payment.get('SEMANA', {'value': 'Sin Semana'})['value']
        if week not in payments_by_week:
            payments_by_week[week] = []
        payments_by_week[week].append(payment)
        
    report = f"📋 *Reporte de Pagos para: {worker_name}*\n{'-'*35}\n"
    grand_total = 0.0

    for week in sorted(payments_by_week.keys()):
        week_payments = payments_by_week[week]
        week_total = 0.0
        report += f"\n🗓️ *{week.upper()}*\n"
        
        for payment in week_payments:
            try:
                amount = float(payment.get('IMPORTE PAGADO', 0.0) or 0.0)
                week_total += amount
                fecha_str = payment.get('FECHA', 'Sin Fecha')
                fecha_formateada = datetime.strptime(fecha_str, '%Y-%m-%d').strftime('%d-%m-%Y')
                report += f"  - `{fecha_formateada}`: `${amount:,.2f}`\n"
            except (ValueError, TypeError):
                continue
        
        report += f"💰 *Total Semana: ${week_total:,.2f}*\n{'-'*35}"
        grand_total += week_total
    
    report += f"\n\n*TOTAL GENERAL PAGADO: ${grand_total:,.2f}*"

    keyboard = [[InlineKeyboardButton("⬅️ Volver al Menú", callback_data="main_menu")]]
    await query.edit_message_text(report, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

# --- Conversation Handler de Mano de Obra (Simplificado) ---
mano_de_obra_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_mo_query, pattern="^start_mo$")
    ],
    states={
        SELECT_WORKER: [
            CallbackQueryHandler(generate_payment_report, pattern="^mo_worker_")
        ],
    },
    fallbacks=[
        CallbackQueryHandler(query_handlers.start, pattern="^main_menu$"),
        CommandHandler("start", query_handlers.start)
    ],
)

