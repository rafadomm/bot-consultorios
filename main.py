# main.py

import config
import query_handlers
import capture_handlers
import mano_de_obra_handlers
import dashboard_handler
from security import restricted
from telegram.ext import Application, CommandHandler

def main() -> None:
    """Inicia el bot y registra los manejadores de forma modular y correcta."""
    
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # 1. Comando /start (Universal y Protegido)
    # Este es nuestro "reseteo" y la puerta de entrada principal.
    application.add_handler(CommandHandler("start", restricted(query_handlers.start)))
    
    # 2. Registramos las conversaciones modulares
    # La seguridad se aplica dentro de cada handler.
    application.add_handler(query_handlers.query_conv_handler)
    application.add_handler(capture_handlers.capture_conv_handler)
    application.add_handler(mano_de_obra_handlers.mano_de_obra_conv_handler)
    application.add_handler(dashboard_handler.dashboard_conv_handler)

    print("🚀 Bot iniciado y escuchando. Presiona Ctrl-C para detener.")
    application.run_polling()

if __name__ == "__main__":
    main()