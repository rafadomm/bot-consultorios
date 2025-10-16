# analytics_queries.py

import baserow_queries
import config
from datetime import datetime

def get_full_analytics():
    """
    Calcula todas las analíticas del proyecto, incluyendo el cálculo correcto de
    las semanas del proyecto.
    """
    all_purchases = baserow_queries._get_all_rows_paginated(config.ID_TABLA_COMPRAS) or []
    all_work_advances = baserow_queries._get_all_rows_paginated(config.ID_TABLA_DESGLOSE_MO) or []

    # --- INICIO DE LA LÓGICA DE SEMANA DE PROYECTO ---

    # 1. Encontrar la fecha de inicio del proyecto (el "Día Cero")
    start_date = None
    all_entries = all_purchases + all_work_advances
    for entry in all_entries:
        date_str = entry.get('FECHA')
        if date_str:
            try:
                current_date = datetime.strptime(date_str, '%Y-%m-%d')
                if start_date is None or current_date < start_date:
                    start_date = current_date
            except ValueError:
                continue
    
    # Si no hay fechas, no podemos calcular, así que salimos de forma segura.
    if start_date is None:
        start_date = datetime.now()

    # --- FIN DE LA LÓGICA DE SEMANA DE PROYECTO ---

    total_purchases = 0.0
    purchases_by_supplier = {}
    weekly_purchase_totals = {}

    for purchase in all_purchases:
        try:
            amount = float(purchase.get('IMPORTE', 0.0) or 0.0)
            total_purchases += amount
            
            if purchase.get('PROVEEDOR') and purchase.get('PROVEEDOR')[0].get('value'):
                supplier_name = purchase['PROVEEDOR'][0]['value']
                purchases_by_supplier[supplier_name] = purchases_by_supplier.get(supplier_name, 0.0) + amount
            
            fecha_str = purchase.get('FECHA')
            if fecha_str:
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                # Calculamos la semana del proyecto
                delta = fecha_obj - start_date
                project_week = (delta.days // 7) + 1
                weekly_purchase_totals[project_week] = weekly_purchase_totals.get(project_week, 0.0) + amount
        except (ValueError, TypeError, IndexError):
            continue

    total_labor_value = 0.0
    labor_by_worker = {}
    weeks = set()
    weekly_labor_totals = {}

    for advance in all_work_advances:
        try:
            amount = float(advance.get('IMPORTE', 0.0) or 0.0)
            total_labor_value += amount
            
            if advance.get('TRABAJADOR') and advance.get('TRABAJADOR').get('value'):
                worker_name = advance['TRABAJADOR']['value']
                labor_by_worker[worker_name] = labor_by_worker.get(worker_name, 0.0) + amount

            fecha_str = advance.get('FECHA')
            if fecha_str:
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                delta = fecha_obj - start_date
                project_week = (delta.days // 7) + 1
                weeks.add(f"SEMANA {project_week}")
                weekly_labor_totals[project_week] = weekly_labor_totals.get(project_week, 0.0) + amount
        except (ValueError, TypeError):
            continue
    
    all_project_weeks = sorted(list(set(weekly_purchase_totals.keys()) | set(weekly_labor_totals.keys())))
    weekly_combined_totals = {
        "labels": [f"S{wk}" for wk in all_project_weeks],
        "purchases": [weekly_purchase_totals.get(wk, 0) for wk in all_project_weeks],
        "labor": [weekly_labor_totals.get(wk, 0) for wk in all_project_weeks]
    }

    return {
        "total_expense": total_purchases + total_labor_value,
        "total_purchases": total_purchases,
        "total_labor": total_labor_value,
        "total_weeks": len(weeks),
        "purchases_by_supplier": dict(sorted(purchases_by_supplier.items(), key=lambda item: item[1], reverse=True)[:10]),
        "labor_by_worker": dict(sorted(labor_by_worker.items(), key=lambda item: item[1], reverse=True)),
        "weekly_combined": weekly_combined_totals
    }