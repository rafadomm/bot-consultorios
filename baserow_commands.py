# baserow_commands.py

import requests
import config
from datetime import date

REQUEST_TIMEOUT = 20 # Aumentamos el timeout para la subida de archivos
HEADERS = {"Authorization": f"Token {config.BASEROW_TOKEN}"}

def create_provider(provider_name):
    """Crea una nueva fila en la tabla PROVEEDORES."""
    url = f"{config.BASEROW_URL}database/rows/table/{config.ID_TABLA_PROVEEDORES}/?user_field_names=true"
    payload = {"Nombre": provider_name}
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT); response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException: return None

def create_product(product_name, provider_id):
    """Crea una nueva fila en la tabla PRECIOS, enlazándola a un proveedor existente."""
    url = f"{config.BASEROW_URL}database/rows/table/{config.ID_TABLA_PRECIOS}/?user_field_names=true"
    payload = {
        "PROVEEDOR": [int(provider_id)],
        "PRODUCTO": product_name
    }
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR CRÍTICO al crear producto: {e}", flush=True)
        return None

# --- ¡LA FUNCIÓN QUE FALTABA! ---
def upload_file(file_bytes, file_name):
    """
    Sube un archivo (foto o PDF) al almacenamiento de Baserow y devuelve los datos necesarios para enlazarlo.
    """
    url = f"{config.BASEROW_URL}user-files/upload-file/"
    try:
        print(f"Subiendo archivo '{file_name}' a Baserow...", flush=True)
        files = {'file': (file_name, file_bytes)}
        response = requests.post(url, headers=HEADERS, files=files, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        uploaded_file_data = response.json()
        print("¡Éxito! Archivo subido.", flush=True)
        # Devolvemos el formato que Baserow espera para un campo de archivo: una lista de diccionarios
        return [uploaded_file_data] 
    except requests.exceptions.RequestException as e:
        print(f"ERROR CRÍTICO al subir archivo: {e}", flush=True)
        if hasattr(e, 'response') and e.response: print(f"Detalle: {e.response.text}", flush=True)
        return None

def create_batch_purchase(items, receipt_data=None):
    """
    Registra una compra con múltiples artículos y opcionalmente enlaza un comprobante.
    """
    url = f"{config.BASEROW_URL}database/rows/table/{config.ID_TABLA_COMPRAS}/batch/?user_field_names=true"
    today = date.today().strftime("%Y-%m-%d")

    payload_items = []
    for item in items:
        payload_items.append({
            "FECHA": today,
            "PRECIOS": [int(item['product_id'])],
            "CANTIDAD": item['quantity'],
            "PRECIO UNITARIO DE COMPRA": item['price']
        })
    
    # Si hay un comprobante, lo añadimos SOLO al primer artículo de la compra.
    if receipt_data and payload_items:
        payload_items[0]['COMPROBANTE'] = receipt_data

    payload = {"items": payload_items}
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT); response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR al guardar lote: {e}", flush=True)
        if hasattr(e, 'response') and e.response: print(f"Detalle: {e.response.text}", flush=True)
        return None