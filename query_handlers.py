# query_handlers.py

import baserow_queries as baserow_client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler
from telegram.constants import ParseMode
from datetime import datetime
import asyncio
import urllib.parse

SELECTING_PROVIDER = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dashboard_url = "https://webapp.dommsoluciones.com/dashboard.html"
    keyboard = [
        [InlineKeyboardButton("Consultar Compras 🛒", callback_data="consultar_compras")],
        [InlineKeyboardButton("Capturar Compra 💸", callback_data="start_capture")],
        [InlineKeyboardButton("👷 Mano de Obra", callback_data="start_mo")],
        [InlineKeyboardButton("📊 Ver Dashboard", callback_data="prepare_dashboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_text = "Menú Principal. ¿Qué deseas hacer?"
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=menu_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text("¡Hola! 👋 Soy tu asistente del proyecto Consultorios-Loft.\n\n¿Qué deseas hacer?", reply_markup=reply_markup)
    return ConversationHandler.END

async def solicitar_proveedor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    await query.edit_message_text(text="Buscando proveedores... ⏳")
    proveedores = baserow_client.get_proveedores()
    if not proveedores:
        await query.edit_message_text(text="❌ Error: No se encontraron proveedores."); return await start(update, context)
    keyboard = [[InlineKeyboardButton(p['value'], callback_data=f"prov_{p['id']}_{p['value']}")] for p in proveedores]
    keyboard.append([InlineKeyboardButton("⬅️ Volver al Menú", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Selecciona un proveedor:", reply_markup=reply_markup)
    return SELECTING_PROVIDER

async def mostrar_compras(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    parts = query.data.split('_', 2); nombre_proveedor = parts[2]
    await query.edit_message_text(text=f"Buscando y agrupando compras de *{nombre_proveedor}*... ⏳", parse_mode=ParseMode.MARKDOWN)
    
    # --- INICIO DE LA LÓGICA DE SEMANA DE PROYECTO ---
    project_start_date = baserow_client.get_project_start_date()
    # --- FIN DE LA LÓGICA ---
    
    compras = baserow_client.get_compras_por_proveedor(nombre_proveedor)
    if not compras:
        await query.edit_message_text(text=f"✅ ¡Conexión exitosa!\n\nℹ️ No se encontraron compras registradas para *{nombre_proveedor}*.", parse_mode=ParseMode.MARKDOWN)
        return SELECTING_PROVIDER
        
    compras_agrupadas = {}
    for compra in compras:
        fecha_str = compra.get('FECHA', 'Sin Fecha')
        if fecha_str not in compras_agrupadas: compras_agrupadas[fecha_str] = []
        compras_agrupadas[fecha_str].append(compra)
        
    header = f"🛒 *Compras a: {nombre_proveedor}*\n{'-'*35}\n"; mensaje_para_imprimir = f"Reporte de Compras\nProveedor: {nombre_proveedor}\n--------------------\n"
    mensajes_telegram = []; mensaje_actual_telegram = ""
    weekly_totals = {}

    for fecha_str in sorted(compras_agrupadas.keys()):
        items_del_dia = compras_agrupadas[fecha_str]; total_diario = 0.0; comprobante_url = None; fecha_obj = None
        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
            fecha_formateada = fecha_obj.strftime('%d-%m-%Y')
        except ValueError:
            fecha_formateada = fecha_str
            
        bloque_dia_telegram = f"🗓️ *Compra del:* {fecha_formateada}\n"; bloque_dia_impresion = f"Compra del: {fecha_formateada}\n"
        
        for item in items_del_dia:
            producto = item.get('Producto', 'Sin descripción'); cantidad = float(item.get('CANTIDAD', 0.0) or 0.0); precio_de_compra = float(item.get('PRECIO UNITARIO DE COMPRA', 0.0) or 0.0)
            total_diario += cantidad * precio_de_compra
            bloque_dia_telegram += f"  - `{cantidad}` x _{producto}_\n"; bloque_dia_impresion += f" - {cantidad} x {producto}\n"
            if not comprobante_url and item.get('ComprobanteURL'): comprobante_url = item.get('ComprobanteURL')
            
        bloque_dia_telegram += f"💰 *Total del día: ${total_diario:,.2f}*\n";
        if comprobante_url: bloque_dia_telegram += f"🧾 [Ver Comprobante]({comprobante_url})\n"
        bloque_dia_telegram += f"{'-'*35}\n"; bloque_dia_impresion += f"Total del dia: ${total_diario:,.2f}\n--------------------\n"

        if fecha_obj and project_start_date:
            # Calculamos la semana del proyecto
            delta = fecha_obj - project_start_date
            project_week = (delta.days // 7) + 1
            if project_week not in weekly_totals: weekly_totals[project_week] = 0.0
            weekly_totals[project_week] += total_diario

        if len(header + mensaje_actual_telegram + bloque_dia_telegram) > 4096:
            mensajes_telegram.append(header + mensaje_actual_telegram); mensaje_actual_telegram = bloque_dia_telegram
        else:
            mensaje_actual_telegram += bloque_dia_telegram
        
        mensaje_para_imprimir += bloque_dia_impresion
    
    if weekly_totals:
        summary_header = f"\n\n📊 *Resumen Semanal del Proyecto*\n{'-'*35}\n"; summary_text_telegram = ""; summary_text_printer = "\nResumen Semanal\n--------------------\n"
        for week_num in sorted(weekly_totals.keys()):
            total_semanal = weekly_totals[week_num]
            summary_text_telegram += f"🗓️ *Semana {week_num}:* ${total_semanal:,.2f}\n"; summary_text_printer += f"Semana {week_num}: ${total_semanal:,.2f}\n"
        
        if len(header + mensaje_actual_telegram + summary_header + summary_text_telegram) > 4096:
            mensajes_telegram.append(header + mensaje_actual_telegram); mensajes_telegram.append(summary_header + summary_text_telegram)
        else:
            mensaje_actual_telegram += summary_header + summary_text_telegram
            mensajes_telegram.append(header + mensaje_actual_telegram)
            
        mensaje_para_imprimir += summary_text_printer
    else:
        mensajes_telegram.append(header + mensaje_actual_telegram)

    encoded_report = urllib.parse.quote(mensaje_para_imprimir); print_url = f"https://webapp.dommsoluciones.com/print.html?data={encoded_report}"
    keyboard = [[InlineKeyboardButton("🖨️ Imprimir Reporte", web_app=WebAppInfo(url=print_url))], [InlineKeyboardButton("⬅️ Volver a Proveedores", callback_data="back_to_providers")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=mensajes_telegram[0], parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    if len(mensajes_telegram) > 1:
        for i, msg in enumerate(mensajes_telegram[1:], start=2):
            await asyncio.sleep(0.5); await context.bot.send_message(chat_id=query.message.chat_id, text=f"*(Parte {i}/{len(mensajes_telegram)})*\n\n{msg}", parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            
    await context.bot.send_message(chat_id=query.message.chat_id, text="Consulta finalizada.", reply_markup=reply_markup)
    
    return SELECTING_PROVIDER

query_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(solicitar_proveedor, pattern="^consultar_compras$")],
    states={ SELECTING_PROVIDER: [ CallbackQueryHandler(mostrar_compras, pattern="^prov_"), CallbackQueryHandler(solicitar_proveedor, pattern="^back_to_providers$"), ], },
    fallbacks=[ CallbackQueryHandler(start, pattern="^main_menu$"), CommandHandler("start", start), ],
)