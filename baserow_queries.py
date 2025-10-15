# baserow_queries.py

import requests
import config

REQUEST_TIMEOUT = 15
HEADERS = {"Authorization": f"Token {config.BASEROW_TOKEN}"}
MAX_ROWS_LIMIT = 200 # Este es el tamaño de cada "página"

def _get_all_rows_paginated(table_id):
    """
    Función interna que obtiene TODAS las filas de una tabla, manejando la paginación.
    """
    all_rows = []
    url = f"{config.BASEROW_URL}database/rows/table/{table_id}/?user_field_names=true&size={MAX_ROWS_LIMIT}"
    
    while url:
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            all_rows.extend(data.get('results', []))
            # Baserow nos da la URL de la siguiente página. Si es 'null', el bucle termina.
            url = data.get('next')
        except requests.exceptions.RequestException as e:
            print(f"Error durante la paginación para la tabla {table_id}: {e}", flush=True)
            return None
            
    return all_rows

def get_proveedores():
    """Obtiene la lista de proveedores desde la tabla PRECIOS."""
    items = _get_all_rows_paginated(config.ID_TABLA_PRECIOS)
    if items is None: return []
    
    proveedores_dict = {}
    for item in items:
        proveedor_data_list = item.get('PROVEEDOR')
        if proveedor_data_list and isinstance(proveedor_data_list, list):
            proveedor = proveedor_data_list[0]
            proveedores_dict[proveedor.get('id')] = proveedor.get('value')
            
    proveedores_unicos = [{'id': pid, 'value': name} for pid, name in proveedores_dict.items()]
    proveedores_unicos.sort(key=lambda x: x['value'])
    return proveedores_unicos

def get_compras_por_proveedor(nombre_proveedor):
    """Obtiene las compras de un proveedor, con paginación completa."""
    # PASO 1: Obtener TODOS los productos
    todos_los_productos = _get_all_rows_paginated(config.ID_TABLA_PRECIOS)
    if todos_los_productos is None: return []
        
    product_ids = set()
    for producto in todos_los_productos:
        proveedor_data_list = producto.get('PROVEEDOR')
        if proveedor_data_list and isinstance(proveedor_data_list, list):
            nombre_en_db = proveedor_data_list[0].get('value', '').strip().lower()
            nombre_buscado = nombre_proveedor.strip().lower()
            if nombre_en_db == nombre_buscado:
                product_ids.add(producto.get('id'))

    if not product_ids: return []
            
    # PASO 2: Obtener TODAS las compras y luego filtrarlas en Python.
    todas_las_compras = _get_all_rows_paginated(config.ID_TABLA_COMPRAS)
    if todas_las_compras is None: return []

    compras_filtradas = []
    for compra in todas_las_compras:
        producto_enlazado = compra.get('PRECIOS')
        if producto_enlazado and isinstance(producto_enlazado, list):
            if producto_enlazado[0].get('id') in product_ids:
                if 'PRECIOS' in compra and compra['PRECIOS']: compra['Producto'] = compra['PRECIOS'][0].get('value')
                if 'COMPROBANTE' in compra and compra['COMPROBANTE']: compra['ComprobanteURL'] = compra['COMPROBANTE'][0].get('url')
                compras_filtradas.append(compra)
                
    return compras_filtradas

def get_products_by_provider(provider_id):
    """
    Obtiene todos los productos de la tabla PRECIOS que pertenecen a un proveedor específico.
    """
    all_products = _get_all_rows_paginated(config.ID_TABLA_PRECIOS)
    if all_products is None:
        return []

    provider_products = []
    for product in all_products:
        provider_data_list = product.get('PROVEEDOR')
        if provider_data_list and isinstance(provider_data_list, list):
            # Comparamos el ID del proveedor del producto con el ID que nos pasaron.
            if str(provider_data_list[0].get('id')) == str(provider_id):
                provider_products.append(product)
    
    return provider_products

def get_product_price(product_id):
    """Obtiene los datos de una sola fila de producto para leer su precio."""
    url = f"{config.BASEROW_URL}database/rows/table/{config.ID_TABLA_PRECIOS}/{product_id}/?user_field_names=true"
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        product_data = response.json()
        # El precio es un lookup, por lo que puede ser una lista
        price_list = product_data.get('PRECIO UNITARIO')
        if price_list and isinstance(price_list, list):
            # Devolvemos el valor numérico del precio
            return float(price_list[0].get('value', '0.0').replace(',', ''))
        # Manejar el caso donde el precio no es una lista (por si cambia el tipo de campo)
        elif price_list:
             return float(str(price_list).replace(',', ''))
        return 0.0 # Devuelve 0.0 si no se encuentra el precio
    except (requests.exceptions.RequestException, ValueError, TypeError):
        return 0.0