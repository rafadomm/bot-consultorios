# main.py
import config, query_handlers, capture_handlers, mano_de_obra_handlers
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

def main() -> None:
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # Comandos y Menú Principal
    application.add_handler(CommandHandler("start", query_handlers.start))
    
    # Conversaciones Modulares
    application.add_handler(query_handlers.query_conv_handler)
    application.add_handler(capture_handlers.capture_conv_handler)
    application.add_handler(mano_de_obra_handlers.mano_de_obra_conv_handler)

    print("🚀 Bot iniciado y escuchando. Presiona Ctrl-C para detener.")
    application.run_polling()

if __name__ == "__main__":
    main()