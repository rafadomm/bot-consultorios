# main.py

import config
import query_handlers
import capture_handlers
from telegram.ext import Application, CommandHandler

def main() -> None:
    """Inicia el bot y registra los manejadores de forma modular."""
    
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # 1. Comando /start (INDEPENDIENTE)
    # Este es nuestro "reseteo" universal. No pertenece a ninguna conversación.
    # Llama a la función 'start' definida en query_handlers.py
    application.add_handler(CommandHandler("start", query_handlers.start))

    # 2. Registramos la conversación de CONSULTA (importada desde query_handlers.py)
    application.add_handler(query_handlers.query_conv_handler)
    
    # 3. Registramos la conversación de CAPTURA (importada desde capture_handlers.py)
    application.add_handler(capture_handlers.capture_conv_handler)

    print("🚀 Bot iniciado y escuchando. Presiona Ctrl-C para detener.")
    application.run_polling()

if __name__ == "__main__":
    main()