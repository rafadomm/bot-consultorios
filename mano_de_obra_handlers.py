# mano_de_obra_handlers.py

import mano_de_obra_queries
import mano_de_obra_commands
import query_handlers
from security import restricted
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
import asyncio

# Estados para la conversación de Mano de Obra
(SELECT_ACTION, 
 SELECT_WORKER_QUERY, SELECT_WEEK_QUERY,
 SELECT_WEEK_ADVANCE, AWAITING_NEW_WEEK, SELECT_WORKER_ADVANCE, SELECT_CONCEPT, AWAITING_NEW_CONCEPT, AWAITING_QUANTITY, AWAITING_PRICE, ADD_ANOTHER_OR_FINISH_ADVANCE,
 SELECT_WORKER_PAYMENT, SELECT_WEEK_PAYMENT, AWAITING_AMOUNT, AWAITING_RECEIPT_CHOICE, AWAITING_RECEIPT_UPLOAD
) = range(30, 46)

async def mano_de_obra_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el sub-menú de Mano de Obra."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📝 Registrar Avance", callback_data="mo_advance")],
        [InlineKeyboardButton("💸 Registrar Pago", callback_data="mo_payment")],
        [InlineKeyboardButton("📋 Consultar Balance", callback_data="mo_query")],
        [InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data="main_menu")]
    ]
    await query.edit_message_text("Módulo de Mano de Obra:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_ACTION

async def cancel_mo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación de mano de obra y vuelve al menú principal."""
    return await query_handlers.start(update, context)

# --- Flujo de Consulta de Balance ---
async def start_balance_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    workers, _ = mano_de_obra_queries.get_workers_and_weeks()
    if not workers:
        await query.edit_message_text("No hay trabajadores registrados.")
        return await cancel_mo(update, context)
    keyboard = [[InlineKeyboardButton(w, callback_data=f"query_worker_{w}")] for w in workers]
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mo")])
    await query.edit_message_text("Consulta de Balance: ¿Para qué trabajador?", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_WORKER_QUERY

async def ask_week_for_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    worker_name = query.data.split('_', 2)[2]
    context.user_data['query_worker'] = worker_name
    _, weeks = mano_de_obra_queries.get_workers_and_weeks()
    if not weeks:
        await query.edit_message_text("No hay semanas registradas.")
        return await cancel_mo(update, context)
    keyboard = [[InlineKeyboardButton(w, callback_data=f"query_week_{w}")] for w in weeks]
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mo")])
    await query.edit_message_text(f"Trabajador: *{worker_name}*\n\n¿De qué semana quieres el reporte?", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_WEEK_QUERY

async def generate_balance_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    week_name = query.data.split('_', 2)[2]
    worker_name = context.user_data['query_worker']
    await query.edit_message_text(f"Generando balance para *{worker_name}* en *{week_name}*...", parse_mode='Markdown')
    balance_data = mano_de_obra_queries.get_balance_for_worker_and_week(worker_name, week_name)
    if balance_data is None:
        await query.edit_message_text("Error al calcular el balance.")
        return await cancel_mo(update, context)
    report = (f"📋 *Balance Semanal*\nTrabajador: *{worker_name}*\nSemana: *{week_name}*\n{'-'*30}\n"
              f"Total de Trabajo: `${balance_data['work_done']:,.2f}`\nTotal Pagado:     `${balance_data['paid']:,.2f}`\n{'-'*30}\n"
              f"💰 *Saldo Pendiente: `${balance_data['balance']:,.2f}`*")
    keyboard = [[InlineKeyboardButton("⬅️ Volver al menú de M.O.", callback_data="start_mo")]]
    await query.edit_message_text(report, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_ACTION

# --- Flujo de Registro de Avance ---
async def start_advance_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    context.user_data['new_advances'] = {'items': []}
    _, weeks = mano_de_obra_queries.get_workers_and_weeks()
    keyboard = [[InlineKeyboardButton(w, callback_data=f"adv_week_{w}")] for w in weeks]
    keyboard.insert(0, [InlineKeyboardButton("[ + ] Crear Nueva Semana", callback_data="new_week")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mo")])
    await query.edit_message_text("Registrar Avance: ¿Para qué semana?", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_WEEK_ADVANCE

async def ask_new_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    await query.edit_message_text("OK. Escribe el nombre de la nueva semana (ej: SEMANA 16):")
    return AWAITING_NEW_WEEK

async def receive_new_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    week_name = update.message.text.upper()
    context.user_data['new_advances']['week'] = week_name
    return await select_worker_for_advance(update, context)

async def select_worker_for_advance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if 'week' not in context.user_data['new_advances']:
        query = update.callback_query; await query.answer()
        context.user_data['new_advances']['week'] = query.data.split('_', 2)[2]
    workers, _ = mano_de_obra_queries.get_workers_and_weeks()
    keyboard = [[InlineKeyboardButton(w, callback_data=f"adv_worker_{w}")] for w in workers]
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mo")])
    message_text = f"Semana: *{context.user_data['new_advances']['week']}*\n\n¿Para qué trabajador?"
    if update.callback_query:
        await update.callback_query.edit_message_text(message_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(message_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_WORKER_ADVANCE

async def select_concept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    context.user_data['new_advances']['worker'] = query.data.split('_', 2)[2]
    concepts = mano_de_obra_queries.get_unique_concepts()
    context.user_data['concepts_list'] = concepts
    keyboard = [[InlineKeyboardButton("[ + ] Escribir Concepto Nuevo", callback_data="new_concept")]]
    for i, c in enumerate(concepts):
        keyboard.append([InlineKeyboardButton(c, callback_data=f"adv_concept_{i}")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mo")])
    await query.edit_message_text("Selecciona un concepto o escribe uno nuevo:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_CONCEPT

async def ask_new_concept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    await query.edit_message_text("OK. Escribe el concepto del trabajo:")
    return AWAITING_NEW_CONCEPT

async def ask_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['current_concept'] = {}
    if update.callback_query:
        query = update.callback_query; await query.answer()
        concept_index = int(query.data.split('_', 2)[2])
        context.user_data['current_concept']['concept'] = context.user_data['concepts_list'][concept_index]
    else:
        context.user_data['current_concept']['concept'] = update.message.text
    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text("Concepto guardado. Ahora, introduce la cantidad (ej: 13.5):")
    return AWAITING_QUANTITY

async def receive_quantity_and_ask_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try: context.user_data['current_concept']['quantity'] = float(update.message.text)
    except ValueError: await update.message.reply_text("Cantidad inválida."); return AWAITING_QUANTITY
    await update.message.reply_text("Cantidad guardada. Ahora, introduce el precio unitario:")
    return AWAITING_PRICE

async def receive_price_and_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try: context.user_data['current_concept']['price'] = float(update.message.text)
    except ValueError: await update.message.reply_text("Precio inválido."); return AWAITING_PRICE
    concept_data = context.user_data['current_concept']
    advances = context.user_data['new_advances']
    advances['items'].append({
        'worker': advances['worker'], 'week': advances['week'], 'concept': concept_data['concept'],
        'quantity': concept_data['quantity'], 'price': concept_data['price']
    })
    summary = f"📝 *Avances para {advances['worker']} - {advances['week']}*\n\n"
    for item in advances['items']: summary += f"- `{item['quantity']}` x _{item['concept']}_ @ `${item['price']:,.2f}`\n"
    keyboard = [[InlineKeyboardButton("[ + ] Añadir Otro Concepto", callback_data="add_another_advance")], [InlineKeyboardButton("✅ Finalizar y Guardar", callback_data="save_advances")]]
    await update.message.reply_text(summary, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_ANOTHER_OR_FINISH_ADVANCE

async def save_advances(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    await query.edit_message_text("Guardando avances en Baserow...")
    all_success = True
    for item in context.user_data['new_advances']['items']:
        result = mano_de_obra_commands.create_single_work_advance(item)
        if not result: all_success = False
        await asyncio.sleep(0.5)
    if all_success: await query.edit_message_text("✅ ¡Todos los avances han sido guardados exitosamente!")
    else: await query.edit_message_text("⚠️ Algunos avances no se pudieron guardar. Revisa los logs.")
    await asyncio.sleep(3)
    return await cancel_mo(update, context)

# --- Flujo de Registro de Pago ---
async def start_payment_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    context.user_data['new_payment'] = {}
    workers, _ = mano_de_obra_queries.get_workers_and_weeks()
    keyboard = [[InlineKeyboardButton(w, callback_data=f"pay_worker_{w}")] for w in workers]
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mo")])
    await query.edit_message_text("Registrar Pago: ¿A qué trabajador?", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_WORKER_PAYMENT

async def select_week_for_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    worker_name = query.data.split('_', 2)[2]
    context.user_data['new_payment']['worker'] = worker_name
    _, weeks = mano_de_obra_queries.get_workers_and_weeks()
    keyboard = [[InlineKeyboardButton(w, callback_data=f"pay_week_{w}")] for w in weeks]
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_mo")])
    await query.edit_message_text(f"Trabajador: *{worker_name}*\n\n¿A qué semana corresponde el pago?", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_WEEK_PAYMENT

async def ask_for_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    week_name = query.data.split('_', 2)[2]
    context.user_data['new_payment']['week'] = week_name
    await query.edit_message_text("OK. Escribe el importe total pagado (ej: 26000.00):")
    return AWAITING_AMOUNT

async def receive_amount_and_ask_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try: context.user_data['new_payment']['amount'] = float(update.message.text)
    except ValueError: await update.message.reply_text("Importe inválido."); return AWAITING_AMOUNT
    keyboard = [[InlineKeyboardButton("📸 Adjuntar Comprobante", callback_data="attach_receipt")], [InlineKeyboardButton("⏩ Omitir y Guardar", callback_data="skip_receipt")]]
    await update.message.reply_text("¿Deseas adjuntar un comprobante para este pago?", reply_markup=InlineKeyboardMarkup(keyboard))
    return AWAITING_RECEIPT_CHOICE

async def ask_for_receipt_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    await query.edit_message_text("OK. Envía la foto o el archivo PDF.")
    return AWAITING_RECEIPT_UPLOAD

async def save_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, receipt_data=None) -> int:
    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text("Guardando pago en Baserow...")
    result = mano_de_obra_commands.create_payment(context.user_data['new_payment'], receipt_data)
    if result: await message.reply_text("✅ ¡Pago guardado exitosamente!")
    else: await message.reply_text("❌ Hubo un error al guardar.")
    await asyncio.sleep(2)
    return await cancel_mo(update, context)

async def save_without_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await save_payment(update, context, receipt_data=None)

async def receive_receipt_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    attachment = update.message.effective_attachment
    if not attachment: await update.message.reply_text("Archivo no válido."); return AWAITING_RECEIPT_UPLOAD
    await update.message.reply_text("Subiendo comprobante... ⏳")
    file = await attachment.get_file(); file_bytes = await file.download_as_bytearray()
    file_name = attachment.file_name or "comprobante_pago.jpg"
    receipt_data = mano_de_obra_commands.upload_file(file_bytes, file_name)
    if not receipt_data: await update.message.reply_text("❌ Error al subir. Guardando sin comprobante...")
    return await save_payment(update, context, receipt_data=receipt_data)

# --- CONVERSATION HANDLER (Al final del archivo y protegido) ---
mano_de_obra_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(restricted(mano_de_obra_menu), pattern="^start_mo$")],
    states={
        SELECT_ACTION: [
            CallbackQueryHandler(start_advance_capture, pattern="^mo_advance$"),
            CallbackQueryHandler(start_payment_capture, pattern="^mo_payment$"),
            CallbackQueryHandler(start_balance_query, pattern="^mo_query$"),
        ],
        # Flujo de Consulta
        SELECT_WORKER_QUERY: [CallbackQueryHandler(ask_week_for_query, pattern="^query_worker_")],
        SELECT_WEEK_QUERY: [CallbackQueryHandler(generate_balance_report, pattern="^query_week_")],
        # Flujo de Registro de Avance
        SELECT_WEEK_ADVANCE: [CallbackQueryHandler(select_worker_for_advance, pattern="^adv_week_"), CallbackQueryHandler(ask_new_week, pattern="^new_week$")],
        AWAITING_NEW_WEEK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_week)],
        SELECT_WORKER_ADVANCE: [CallbackQueryHandler(select_concept, pattern="^adv_worker_")],
        SELECT_CONCEPT: [CallbackQueryHandler(ask_quantity, pattern="^adv_concept_"), CallbackQueryHandler(ask_new_concept, pattern="^new_concept$")],
        AWAITING_NEW_CONCEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quantity)],
        AWAITING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity_and_ask_price)],
        AWAITING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price_and_summarize)],
        ADD_ANOTHER_OR_FINISH_ADVANCE: [CallbackQueryHandler(select_concept, pattern="^add_another_advance$"), CallbackQueryHandler(save_advances, pattern="^save_advances$")],
        # Flujo de Registro de Pago
        SELECT_WORKER_PAYMENT: [CallbackQueryHandler(select_week_for_payment, pattern="^pay_worker_")],
        SELECT_WEEK_PAYMENT: [CallbackQueryHandler(ask_for_amount, pattern="^pay_week_")],
        AWAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount_and_ask_receipt)],
        AWAITING_RECEIPT_CHOICE: [CallbackQueryHandler(ask_for_receipt_upload, pattern="^attach_receipt$"), CallbackQueryHandler(save_without_receipt, pattern="^skip_receipt$")],
        AWAITING_RECEIPT_UPLOAD: [MessageHandler(filters.PHOTO | filters.Document.ALL, receive_receipt_and_save)],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_mo, pattern="^cancel_mo$"),
        CallbackQueryHandler(query_handlers.start, pattern="^main_menu$"),
        CommandHandler("start", cancel_mo)
    ],
)