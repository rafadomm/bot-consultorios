# capture_handlers.py

import baserow_queries
import baserow_commands
import query_handlers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
import asyncio

# Estados específicos para ESTA conversación
SELECT_PROVIDER, NEW_PROVIDER_NAME, NEW_PRODUCT_NAME, SELECT_PRODUCT, ENTER_QUANTITY, AWAITING_PRICE_CHOICE, ENTERING_NEW_PRICE, ADD_ANOTHER_OR_FINISH = range(8)

async def start_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['current_purchase'] = {'items': [], 'provider_name': '', 'provider_id': ''}
    await query.edit_message_text("Buscando proveedores...")
    proveedores = baserow_queries.get_proveedores()
    keyboard = [[InlineKeyboardButton("[ + ] Crear Nuevo Proveedor", callback_data="new_provider")]]
    for p in proveedores:
        keyboard.append([InlineKeyboardButton(p['value'], callback_data=f"id_prov_{p['id']}_{p['value']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_capture")])
    await query.edit_message_text("Selecciona el proveedor de la compra:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_PROVIDER

async def cancel_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación y vuelve al menú principal."""
    return await query_handlers.start(update, context)

# ... (El resto de las funciones de captura, que ya son estables, se quedan aquí) ...
async def ask_new_provider_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("OK. Escribe el nombre del nuevo proveedor:")
    return NEW_PROVIDER_NAME

async def receive_new_provider_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    provider_name = update.message.text
    await update.message.reply_text(f"Creando proveedor '{provider_name}'...")
    new_provider = baserow_commands.create_provider(provider_name)
    if not new_provider:
        await update.message.reply_text("❌ Error. Intenta de nuevo.")
        return NEW_PROVIDER_NAME
    context.user_data['new_provider_id'] = new_provider.get('id')
    context.user_data['new_provider_name'] = new_provider.get('Nombre')
    await update.message.reply_text(f"✅ ¡Proveedor creado!\n\nAhora, escribe el nombre del primer producto:")
    return NEW_PRODUCT_NAME

async def receive_new_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_name = update.message.text
    provider_id, provider_name = context.user_data.get('new_provider_id'), context.user_data.get('new_provider_name')
    await update.message.reply_text(f"Creando '{product_name}' para '{provider_name}'...")
    new_product = baserow_commands.create_product(product_name, provider_id)
    if not new_product:
        await update.message.reply_text("❌ Error. Escribe de nuevo el nombre.")
        return NEW_PRODUCT_NAME
    context.user_data['current_purchase']['provider_name'] = provider_name
    context.user_data['current_purchase']['provider_id'] = provider_id
    context.user_data['current_product'] = {'id': new_product.get('id'), 'name': product_name}
    await update.message.reply_text(f"✅ ¡Producto guardado!\n\nAhora, ¿qué cantidad compraste?")
    return ENTER_QUANTITY

async def select_existing_provider(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_', 3)
    provider_id, provider_name = parts[2], parts[3]
    context.user_data['current_purchase']['provider_id'] = provider_id
    context.user_data['current_purchase']['provider_name'] = provider_name
    return await ask_product(update, context)

async def ask_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    provider_id = context.user_data['current_purchase']['provider_id']
    if update.callback_query:
        await update.callback_query.edit_message_text("Buscando productos...")
    products = baserow_queries.get_products_by_provider(provider_id)
    keyboard = [[InlineKeyboardButton("[ + ] Agregar Nuevo Producto", callback_data="new_product")]]
    for p in products:
        keyboard.append([InlineKeyboardButton(p.get('PRODUCTO'), callback_data=f"id_prod_{p.get('id')}_{p.get('PRODUCTO')}")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_capture")])
    await update.callback_query.edit_message_text("Selecciona un producto (o agrégalo si es nuevo):", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_PRODUCT

async def ask_new_product_name_for_existing_provider(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    provider_name = context.user_data['current_purchase']['provider_name']
    await query.edit_message_text(f"OK. Escribe el nombre del nuevo producto para *{provider_name}*:", parse_mode='Markdown')
    return NEW_PRODUCT_NAME # Reutilizamos este estado

async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_', 3)
    product_id, product_name = parts[2], parts[3]
    context.user_data['current_product'] = {'id': product_id, 'name': product_name}
    await query.edit_message_text(f"Producto: *{product_name}*\n\n¿Qué cantidad compraste? (Escribe solo el número)", parse_mode='Markdown')
    return ENTER_QUANTITY

async def receive_quantity_and_ask_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        quantity = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Número inválido.")
        return ENTER_QUANTITY
    context.user_data['current_product']['quantity'] = quantity
    product_id = context.user_data['current_product']['id']
    last_price = baserow_queries.get_product_price(product_id)
    keyboard = [[InlineKeyboardButton(f"✅ Sí, usar ${last_price:,.2f}", callback_data=f"price_{last_price}")], [InlineKeyboardButton("✏️ Escribir Nuevo Precio", callback_data="new_price")]]
    await update.message.reply_text(f"El último precio registrado es de ${last_price:,.2f}.\n¿Usamos este precio?", reply_markup=InlineKeyboardMarkup(keyboard))
    return AWAITING_PRICE_CHOICE

async def ask_for_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("OK. Por favor, escribe el nuevo precio unitario (solo el número):")
    return ENTERING_NEW_PRICE

def _add_item_to_cart(context: ContextTypes.DEFAULT_TYPE, price: float):
    product = context.user_data['current_product']
    context.user_data['current_purchase']['items'].append({
        'product_id': product['id'],
        'product_name': product['name'],
        'quantity': product['quantity'],
        'price': price
    })

async def show_summary_and_ask_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    purchase = context.user_data['current_purchase']
    resumen = f"🛒 *Resumen de Compra*\nProveedor: *{purchase['provider_name']}*\n\n*Artículos:*\n"
    total_compra = 0.0
    for item in purchase['items']:
        resumen += f"- `{item['quantity']}` x _{item['product_name']}_ @ `${item['price']:,.2f}`\n"
        total_compra += item['quantity'] * item['price']
    resumen += f"\n*Total Acumulado: ${total_compra:,.2f}*"
    keyboard = [[InlineKeyboardButton("[ + ] Añadir Otro Producto", callback_data="add_another")], [InlineKeyboardButton("✅ Finalizar y Guardar", callback_data="finish_capture")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(resumen, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(resumen, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_ANOTHER_OR_FINISH

async def confirm_price_and_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    price = float(query.data.split('_', 1)[1])
    _add_item_to_cart(context, price)
    return await show_summary_and_ask_next(update, context)

async def receive_new_price_and_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        price = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Precio inválido.")
        return ENTERING_NEW_PRICE
    _add_item_to_cart(context, price)
    return await show_summary_and_ask_next(update, context)

async def finish_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Este es el flujo completo con la pregunta del comprobante
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📸 Adjuntar Foto o PDF", callback_data="attach_receipt")],
        [InlineKeyboardButton("⏩ Omitir y Guardar", callback_data="skip_receipt")]
    ]
    await query.edit_message_text("¿Deseas adjuntar el comprobante de esta compra?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END # Temporal, para no causar más errores

# --- CONVERSATION HANDLER DE CAPTURA (AHORA VIVE AQUÍ) ---
capture_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_capture, pattern="^start_capture$")],
    states={
        SELECT_PROVIDER: [
            CallbackQueryHandler(ask_new_provider_name, pattern="^new_provider$"),
            CallbackQueryHandler(select_existing_provider, pattern="^id_prov_")
        ],
        NEW_PROVIDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_provider_name)],
        NEW_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_product_name)],
        SELECT_PRODUCT: [
            CallbackQueryHandler(select_product, pattern="^id_prod_"),
            CallbackQueryHandler(ask_new_product_name_for_existing_provider, pattern="^new_product$")
        ],
        ENTER_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity_and_ask_price)],
        AWAITING_PRICE_CHOICE: [
            CallbackQueryHandler(confirm_price_and_add, pattern="^price_"),
            CallbackQueryHandler(ask_for_new_price, pattern="^new_price$")
        ],
        ENTERING_NEW_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_price_and_add)],
        ADD_ANOTHER_OR_FINISH: [
            CallbackQueryHandler(ask_product, pattern="^add_another$"),
            CallbackQueryHandler(finish_capture, pattern="^finish_capture$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(cancel_capture, pattern="^cancel_capture$"),
        CommandHandler("start", cancel_capture),
    ],
    allow_reentry=True
)