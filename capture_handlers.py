# capture_handlers.py

import baserow_queries
import baserow_commands
import query_handlers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
import asyncio

# Estados específicos para ESTA conversación
SELECT_PROVIDER, NEW_PROVIDER_NAME, NEW_PRODUCT_NAME, SELECT_PRODUCT, ENTER_QUANTITY, ADD_ANOTHER_OR_FINISH = range(6)

async def start_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    context.user_data['current_purchase'] = {'items': [], 'provider_name': '', 'provider_id': ''}
    await query.edit_message_text("Buscando proveedores..."); proveedores = baserow_queries.get_proveedores()
    keyboard = [[InlineKeyboardButton("[ + ] Crear Nuevo Proveedor", callback_data="new_provider")]]
    for p in proveedores: keyboard.append([InlineKeyboardButton(p['value'], callback_data=f"id_prov_{p['id']}_{p['value']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_capture")])
    await query.edit_message_text("Selecciona el proveedor:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_PROVIDER

async def ask_new_provider_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    await query.edit_message_text("OK. Escribe el nombre del nuevo proveedor:")
    return NEW_PROVIDER_NAME

async def receive_new_provider_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    provider_name = update.message.text
    await update.message.reply_text(f"Creando proveedor '{provider_name}'...")
    new_provider = baserow_commands.create_provider(provider_name)
    if not new_provider: await update.message.reply_text("❌ Error. Intenta de nuevo."); return NEW_PROVIDER_NAME
    context.user_data['new_provider_id'] = new_provider.get('id'); context.user_data['new_provider_name'] = new_provider.get('Nombre')
    await update.message.reply_text(f"✅ ¡Proveedor creado!\n\nAhora, escribe el nombre del primer producto:"); return NEW_PRODUCT_NAME

async def receive_new_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_name = update.message.text
    provider_id, provider_name = context.user_data.get('new_provider_id'), context.user_data.get('new_provider_name')
    await update.message.reply_text(f"Creando '{product_name}' para '{provider_name}'...")
    new_product = baserow_commands.create_product(product_name, provider_id)
    if not new_product: await update.message.reply_text("❌ Error. Escribe de nuevo el nombre."); return NEW_PRODUCT_NAME
    context.user_data['current_purchase']['provider_name'] = provider_name; context.user_data['current_purchase']['provider_id'] = provider_id
    context.user_data['current_product'] = {'id': new_product.get('id'), 'name': product_name}
    await update.message.reply_text(f"✅ ¡Producto guardado!\n\nAhora, ¿qué cantidad compraste?"); return ENTER_QUANTITY

async def select_existing_provider(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    parts = query.data.split('_', 3); provider_id, provider_name = parts[2], parts[3]
    context.user_data['current_purchase']['provider_id'] = provider_id; context.user_data['current_purchase']['provider_name'] = provider_name
    return await ask_product(update, context)

async def ask_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    provider_id = context.user_data['current_purchase']['provider_id']
    if update.callback_query: await update.callback_query.edit_message_text("Buscando productos...")
    products = baserow_queries.get_products_by_provider(provider_id)
    if not products:
        await update.callback_query.edit_message_text("Este proveedor no tiene productos registrados.")
        return await cancel_capture(update, context)
    keyboard = [[InlineKeyboardButton(p.get('PRODUCTO'), callback_data=f"id_prod_{p.get('id')}_{p.get('PRODUCTO')}")] for p in products]
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_capture")])
    await update.callback_query.edit_message_text("Selecciona un producto:", reply_markup=InlineKeyboardMarkup(keyboard)); return SELECT_PRODUCT

async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    parts = query.data.split('_', 3); product_id, product_name = parts[2], parts[3]
    context.user_data['current_product'] = {'id': product_id, 'name': product_name}
    await query.edit_message_text(f"Producto: *{product_name}*\n\n¿Qué cantidad compraste?", parse_mode='Markdown'); return ENTER_QUANTITY

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try: quantity = float(update.message.text)
    except ValueError: await update.message.reply_text("Número inválido."); return ENTER_QUANTITY
    product = context.user_data['current_product']
    context.user_data['current_purchase']['items'].append({'product_id': product['id'], 'product_name': product['name'], 'quantity': quantity})
    purchase = context.user_data['current_purchase']
    resumen = f"🛒 *Resumen de Compra*\nProveedor: *{purchase['provider_name']}*\n\n*Artículos:*\n";
    for item in purchase['items']: resumen += f"- `{item['quantity']}` x _{item['product_name']}_\n"
    keyboard = [[InlineKeyboardButton("[ + ] Añadir Otro Producto", callback_data="add_another")], [InlineKeyboardButton("✅ Finalizar y Guardar", callback_data="finish_capture")]]
    await update.message.reply_text(resumen, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard)); return ADD_ANOTHER_OR_FINISH

async def finish_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    await query.edit_message_text("Guardando tu compra en Baserow...")
    items_to_save = context.user_data['current_purchase']['items']
    result = baserow_commands.create_batch_purchase(items_to_save)
    if result: await query.edit_message_text("✅ ¡Compra guardada exitosamente!")
    else: await query.edit_message_text("❌ Hubo un error al guardar tu compra.")
    context.user_data.clear()
    await asyncio.sleep(2); return await query_handlers.start(update, context)

async def cancel_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query: await update.callback_query.answer()
    return await query_handlers.start(update, context)

# --- CONVERSATION HANDLER DE CAPTURA ---
capture_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_capture, pattern="^start_capture$")],
    states={
        SELECT_PROVIDER: [
            CallbackQueryHandler(ask_new_provider_name, pattern="^new_provider$"),
            CallbackQueryHandler(select_existing_provider, pattern="^id_prov_")
        ],
        NEW_PROVIDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_provider_name)],
        NEW_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_product_name)],
        SELECT_PRODUCT: [CallbackQueryHandler(select_product, pattern="^id_prod_")],
        ENTER_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity)], # Modificado para no preguntar precio
        ADD_ANOTHER_OR_FINISH: [
            CallbackQueryHandler(ask_product, pattern="^add_another$"),
            CallbackQueryHandler(finish_capture, pattern="^finish_capture$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(cancel_capture, pattern="^cancel_capture$"),
        CommandHandler("start", cancel_capture)
    ],
    allow_reentry=True
)