# capture_handlers.py

import baserow_queries
import baserow_commands
import query_handlers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
import asyncio

# Estados de la Conversación
(SELECT_PROVIDER, NEW_PROVIDER_NAME, NEW_PRODUCT_NAME, SELECT_PRODUCT, ENTER_QUANTITY, 
 AWAITING_PRICE_CHOICE, ENTERING_NEW_PRICE, ADD_ANOTHER_OR_FINISH, 
 AWAITING_RECEIPT_CHOICE, AWAITING_RECEIPT_UPLOAD) = range(6, 16)

# ... (Todas las funciones hasta 'ask_for_receipt_upload' se quedan exactamente igual) ...
async def start_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    context.user_data['current_purchase'] = {'items': [], 'provider_name': '', 'provider_id': ''}
    await query.edit_message_text("Buscando proveedores..."); proveedores = baserow_queries.get_proveedores()
    keyboard = [[InlineKeyboardButton("[ + ] Crear Nuevo Proveedor", callback_data="new_provider")]]
    for p in proveedores: keyboard.append([InlineKeyboardButton(p['value'], callback_data=f"id_prov_{p['id']}_{p['value']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_capture")])
    await query.edit_message_text("Selecciona el proveedor:", reply_markup=InlineKeyboardMarkup(keyboard)); return SELECT_PROVIDER
async def ask_new_provider_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    await query.edit_message_text("OK. Escribe el nombre del nuevo proveedor:"); return NEW_PROVIDER_NAME
async def receive_new_provider_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    provider_name = update.message.text
    await update.message.reply_text(f"Creando proveedor '{provider_name}'..."); new_provider = baserow_commands.create_provider(provider_name)
    if not new_provider: await update.message.reply_text("❌ Error. Intenta de nuevo."); return NEW_PROVIDER_NAME
    context.user_data['new_provider_id'] = new_provider.get('id'); context.user_data['new_provider_name'] = new_provider.get('Nombre')
    await update.message.reply_text(f"✅ ¡Proveedor creado!\n\nAhora, escribe el nombre del primer producto:"); return NEW_PRODUCT_NAME
async def receive_new_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_name = update.message.text
    provider_id, provider_name = context.user_data.get('new_provider_id'), context.user_data.get('new_provider_name')
    await update.message.reply_text(f"Creando '{product_name}' para '{provider_name}'..."); new_product = baserow_commands.create_product(product_name, provider_id)
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
        await update.callback_query.edit_message_text("Este proveedor no tiene productos."); return await cancel_capture(update, context)
    keyboard = [[InlineKeyboardButton(p.get('PRODUCTO'), callback_data=f"id_prod_{p.get('id')}_{p.get('PRODUCTO')}")] for p in products]
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_capture")])
    await update.callback_query.edit_message_text("Selecciona un producto:", reply_markup=InlineKeyboardMarkup(keyboard)); return SELECT_PRODUCT
async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    parts = query.data.split('_', 3); product_id, product_name = parts[2], parts[3]
    context.user_data['current_product'] = {'id': product_id, 'name': product_name}
    await query.edit_message_text(f"Producto: *{product_name}*\n\n¿Qué cantidad compraste? (Escribe solo el número)", parse_mode='Markdown'); return ENTER_QUANTITY
async def receive_quantity_and_ask_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try: quantity = float(update.message.text)
    except ValueError: await update.message.reply_text("Número inválido."); return ENTER_QUANTITY
    context.user_data['current_product']['quantity'] = quantity; product_id = context.user_data['current_product']['id']
    last_price = baserow_queries.get_product_price(product_id)
    keyboard = [[InlineKeyboardButton(f"✅ Sí, usar ${last_price:,.2f}", callback_data=f"price_{last_price}")], [InlineKeyboardButton("✏️ Escribir Nuevo Precio", callback_data="new_price")]]
    await update.message.reply_text(f"El último precio registrado es de ${last_price:,.2f}.\n¿Usamos este precio?", reply_markup=InlineKeyboardMarkup(keyboard))
    return AWAITING_PRICE_CHOICE
async def ask_for_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    await query.edit_message_text("OK. Por favor, escribe el nuevo precio unitario (solo el número):"); return ENTERING_NEW_PRICE
def _add_item_to_cart(context: ContextTypes.DEFAULT_TYPE, price: float):
    product = context.user_data['current_product']
    context.user_data['current_purchase']['items'].append({'product_id': product['id'], 'product_name': product['name'], 'quantity': product['quantity'], 'price': price})
async def show_summary_and_ask_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    purchase = context.user_data['current_purchase']; resumen = f"🛒 *Resumen de Compra*\nProveedor: *{purchase['provider_name']}*\n\n*Artículos:*\n"; total_compra = 0.0
    for item in purchase['items']: resumen += f"- `{item['quantity']}` x _{item['product_name']}_ @ `${item['price']:,.2f}`\n"; total_compra += item['quantity'] * item['price']
    resumen += f"\n*Total Acumulado: ${total_compra:,.2f}*"; keyboard = [[InlineKeyboardButton("[ + ] Añadir Otro Producto", callback_data="add_another")], [InlineKeyboardButton("✅ Finalizar Compra", callback_data="finish_items")]]
    if update.callback_query: await update.callback_query.edit_message_text(resumen, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else: await update.message.reply_text(resumen, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_ANOTHER_OR_FINISH
async def confirm_price_and_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer(); price = float(query.data.split('_', 1)[1]); _add_item_to_cart(context, price)
    return await show_summary_and_ask_next(update, context)
async def receive_new_price_and_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try: price = float(update.message.text)
    except ValueError: await update.message.reply_text("Precio inválido."); return ENTERING_NEW_PRICE
    _add_item_to_cart(context, price); return await show_summary_and_ask_next(update, context)

async def ask_for_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📸 Adjuntar Foto o PDF", callback_data="attach_receipt")],
        [InlineKeyboardButton("⏩ Omitir y Guardar", callback_data="skip_receipt")]
    ]
    await query.edit_message_text("¿Deseas adjuntar el comprobante de esta compra?", reply_markup=InlineKeyboardMarkup(keyboard))
    return AWAITING_RECEIPT_CHOICE

async def ask_for_receipt_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("OK. Envía la foto o el archivo PDF del comprobante.")
    return AWAITING_RECEIPT_UPLOAD

# --- ¡FUNCIÓN CON LA CORRECCIÓN! ---
async def save_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, receipt_data=None) -> int:
    """Función central para guardar la compra, con o sin comprobante."""
    # Determinamos si el update vino de un botón o de un mensaje de texto/foto
    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text("Guardando tu compra en Baserow...")
    
    items_to_save = context.user_data['current_purchase']['items']
    result = baserow_commands.create_batch_purchase(items_to_save, receipt_data)
    
    if result:
        await message.reply_text("✅ ¡Compra guardada exitosamente!")
    else:
        await message.reply_text("❌ Hubo un error al guardar tu compra.")
        
    context.user_data.clear()
    await asyncio.sleep(2)

    # ¡LA SOLUCIÓN! Simplemente llamamos a la función `start` con el `update` original.
    # La función `start` ya sabe cómo manejar si es un mensaje o un botón.
    return await query_handlers.start(update, context)

async def save_without_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await save_purchase(update, context, receipt_data=None)

async def receive_receipt_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    attachment = update.message.effective_attachment
    if not attachment:
        await update.message.reply_text("No enviaste un archivo. Por favor, envía una foto o PDF.")
        return AWAITING_RECEIPT_UPLOAD
    await update.message.reply_text("Descargando y subiendo comprobante... ⏳")
    file = await attachment.get_file()
    file_bytes = await file.download_as_bytearray()
    file_name = attachment.file_name or "comprobante.jpg"
    receipt_data = baserow_commands.upload_file(file_bytes, file_name)
    if not receipt_data:
        await update.message.reply_text("❌ Hubo un error al subir el archivo. Guardando la compra sin comprobante...")
    return await save_purchase(update, context, receipt_data=receipt_data)

async def cancel_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query: await update.callback_query.answer()
    return await query_handlers.start(update, context)

capture_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_capture, pattern="^start_capture$")],
    states={
        SELECT_PROVIDER: [ CallbackQueryHandler(ask_new_provider_name, pattern="^new_provider$"), CallbackQueryHandler(select_existing_provider, pattern="^id_prov_")],
        NEW_PROVIDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_provider_name)],
        NEW_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_product_name)],
        SELECT_PRODUCT: [CallbackQueryHandler(select_product, pattern="^id_prod_")],
        ENTER_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity_and_ask_price)],
        AWAITING_PRICE_CHOICE: [ CallbackQueryHandler(confirm_price_and_add, pattern="^price_"), CallbackQueryHandler(ask_for_new_price, pattern="^new_price$")],
        ENTERING_NEW_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_price_and_add)],
        ADD_ANOTHER_OR_FINISH: [ 
            CallbackQueryHandler(ask_product, pattern="^add_another$"), 
            CallbackQueryHandler(ask_for_receipt, pattern="^finish_items$")
        ],
        AWAITING_RECEIPT_CHOICE: [
            CallbackQueryHandler(ask_for_receipt_upload, pattern="^attach_receipt$"),
            CallbackQueryHandler(save_without_receipt, pattern="^skip_receipt$")
        ],
        AWAITING_RECEIPT_UPLOAD: [
            MessageHandler(filters.PHOTO | filters.Document.ALL, receive_receipt_and_save)
        ]
    },
    fallbacks=[ CallbackQueryHandler(cancel_capture, pattern="^cancel_capture$"), CommandHandler("start", cancel_capture) ],
    allow_reentry=True
)