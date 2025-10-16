# main.py

import config
import query_handlers, capture_handlers, mano_de_obra_handlers
import dashboard_handler # ¡NUEVO IMPORT!
from telegram.ext import Application, CommandHandler

def main() -> None:
    """Inicia el bot y registra los manejadores de forma modular y correcta."""
    
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # 1. Comando /start (Universal)
    application.add_handler(CommandHandler("start", query_handlers.start))
    
    # 2. Registramos las conversaciones modulares
    application.add_handler(query_handlers.query_conv_handler)
    application.add_handler(capture_handlers.capture_conv_handler)
    application.add_handler(mano_de_obra_handlers.mano_de_obra_conv_handler)

    # 3. ¡CORRECCIÓN! Registramos el NUEVO ConversationHandler para el dashboard
    application.add_handler(dashboard_handler.dashboard_conv_handler)

    print("🚀 Bot iniciado y escuchando. Presiona Ctrl-C para detener.")
    application.run_polling()

if __name__ == "__main__":
    main()