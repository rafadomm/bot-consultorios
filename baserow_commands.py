# baserow_commands.py

import requests
import config
from datetime import date

REQUEST_TIMEOUT = 20
HEADERS = {"Authorization": f"Token {config.BASEROW_TOKEN}"}

def create_provider(provider_name):
    """Crea una nueva fila en la tabla PROVEEDORES."""
    url = f"{config.BASEROW_URL}database/rows/table/{config.ID_TABLA_PROVEEDORES}/?user_field_names=true"
    payload = {"Nombre": provider_name}
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR al crear proveedor: {e}", flush=True)
        return None

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
        print(f"ERROR al crear producto: {e}", flush=True)
        return None

def upload_file(file_bytes, file_name):
    """Sube un archivo (foto o PDF) y devuelve los datos para enlazarlo."""
    url = f"{config.BASEROW_URL}user-files/upload-file/"
    try:
        files = {'file': (file_name, file_bytes)}
        response = requests.post(url, headers=HEADERS, files=files, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return [response.json()] 
    except requests.exceptions.RequestException as e:
        print(f"ERROR CRÍTICO al subir archivo: {e}", flush=True)
        return None

def create_batch_purchase(items, receipt_data=None):
    """Registra una compra con múltiples artículos y opcionalmente enlaza un comprobante."""
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
    if receipt_data and payload_items:
        payload_items[0]['COMPROBANTE'] = receipt_data
    payload = {"items": payload_items}
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR al guardar lote de compras: {e}", flush=True)
        if hasattr(e, 'response') and e.response: print(f"Detalle: {e.response.text}", flush=True)
        return None