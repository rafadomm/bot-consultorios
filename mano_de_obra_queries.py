# mano_de_obra_queries.py

import baserow_queries
import config

def get_mo_workers_and_weeks():
    """Obtiene listas únicas de trabajadores y semanas desde la tabla DESGLOSE MANO DE OBRA."""
    all_rows = baserow_queries._get_all_rows_paginated(config.ID_TABLA_DESGLOSE_MO)
    if all_rows is None:
        return [], []

    workers = set()
    weeks = set()
    for row in all_rows:
        if row.get('TRABAJADOR') and row['TRABAJADOR']['value']:
            workers.add(row['TRABAJADOR']['value'])
        if row.get('SEMANA') and row['SEMANA']['value']:
            weeks.add(row['SEMANA']['value'])
    
    return sorted(list(workers)), sorted(list(weeks))

def get_work_details(worker_name, week_name):
    """Obtiene el desglose de conceptos y el total para un trabajador y semana."""
    all_rows = baserow_queries._get_all_rows_paginated(config.ID_TABLA_DESGLOSE_MO)
    if all_rows is None:
        return None

    work_details = []
    total_amount = 0.0
    for row in all_rows:
        worker_match = row.get('TRABAJADOR') and row['TRABAJADOR']['value'] == worker_name
        week_match = row.get('SEMANA') and row['SEMANA']['value'] == week_name
        if worker_match and week_match:
            try:
                # --- ¡CORRECCIÓN! ---
                # Añadimos la fila completa a los detalles.
                work_details.append(row)
                amount = float(row.get('IMPORTE', 0.0) or 0.0)
                total_amount += amount
            except (ValueError, TypeError):
                continue
                
    return {
        "details": work_details,
        "total": total_amount
    }

