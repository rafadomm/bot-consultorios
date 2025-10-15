# baserow_commands.py

import requests
import config
from datetime import date

REQUEST_TIMEOUT = 15
HEADERS = {"Authorization": f"Token {config.BASEROW_TOKEN}"}

# ... (las funciones 'create_provider' y 'create_product' se quedan igual) ...
def create_provider(provider_name):
    url = f"{config.BASEROW_URL}database/rows/table/{config.ID_TABLA_PROVEEDORES}/?user_field_names=true"
    payload = {"Nombre": provider_name}
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT); response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException: return None

def create_product(product_name, provider_id, unit_price=0.0):
    url = f"{config.BASEROW_URL}database/rows/table/{config.ID_TABLA_PRECIOS}/?user_field_names=true"
    payload = {"PROVEEDOR": [provider_id], "PRODUCTO": product_name, "PRECIO UNITARIO": unit_price}
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT); response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException: return None

def create_batch_purchase(items):
    """
    Registra una compra con múltiples artículos, incluyendo el precio de compra.
    """
    url = f"{config.BASEROW_URL}database/rows/table/{config.ID_TABLA_COMPRAS}/batch/?user_field_names=true"
    today = date.today().strftime("%Y-%m-%d")

    payload_items = []
    for item in items:
        payload_items.append({
            "FECHA": today,
            "PRECIOS": [int(item['product_id'])], # Enlace al producto
            "CANTIDAD": item['quantity'],
            "PRECIO UNITARIO DE COMPRA": item['price'] # <-- ¡NUEVO CAMPO!
        })
    
    payload = {"items": payload_items}
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT); response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR al guardar lote: {e}", flush=True)
        if hasattr(e, 'response') and e.response: print(f"Detalle: {e.response.text}", flush=True)
        return None