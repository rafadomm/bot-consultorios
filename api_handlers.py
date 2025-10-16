# api_handlers.py

import json
from telegram import Update
from telegram.ext import ContextTypes
import baserow_queries
import mano_de_obra_queries

async def get_dashboard_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Esta función se activa cuando la Web App pide los datos.
    Calcula todas las analíticas y las devuelve como JSON.
    """
    print("API: Solicitud de datos para el dashboard recibida.", flush=True)
    
    # 1. Calcular totales de compras y por proveedor
    all_purchases = baserow_queries._get_all_rows_paginated(config.ID_TABLA_COMPRAS)
    total_purchases = 0
    purchases_by_supplier = {}
    if all_purchases:
        for purchase in all_purchases:
            try:
                amount = float(purchase.get('IMPORTE', 0.0) or 0.0)
                total_purchases += amount
                
                # Agrupar por proveedor
                if purchase.get('PROVEEDOR') and purchase['PROVEEDOR'][0].get('value'):
                    supplier_name = purchase['PROVEEDOR'][0]['value']
                    if supplier_name not in purchases_by_supplier:
                        purchases_by_supplier[supplier_name] = 0.0
                    purchases_by_supplier[supplier_name] += amount
            except (ValueError, TypeError, IndexError):
                continue

    # 2. Calcular totales de mano de obra y por trabajador
    all_labor_payments = baserow_queries._get_all_rows_paginated(config.ID_TABLA_PAGOS_MO)
    total_labor = 0
    labor_by_worker = {}
    weeks = set()
    if all_labor_payments:
        for payment in all_labor_payments:
            try:
                amount = float(payment.get('IMPORTE PAGADO', 0.0) or 0.0)
                total_labor += amount

                # Agrupar por trabajador
                if payment.get('TRABAJADOR') and payment['TRABAJADOR'].get('value'):
                    worker_name = payment['TRABAJADOR']['value']
                    if worker_name not in labor_by_worker:
                        labor_by_worker[worker_name] = 0.0
                    labor_by_worker[worker_name] += amount

                # Contar semanas únicas
                if payment.get('SEMANA') and payment['SEMANA'].get('value'):
                    weeks.add(payment['SEMANA']['value'])
            except (ValueError, TypeError):
                continue
    
    # 3. Consolidar todos los datos en un solo objeto
    dashboard_data = {
        "total_expense": total_purchases + total_labor,
        "total_purchases": total_purchases,
        "total_labor": total_labor,
        "total_weeks": len(weeks),
        "purchases_by_supplier": dict(sorted(purchases_by_supplier.items(), key=lambda item: item[1], reverse=True)),
        "labor_by_worker": dict(sorted(labor_by_worker.items(), key=lambda item: item[1], reverse=True))
    }

    # 4. Devolver los datos como una respuesta JSON
    await update.message.reply_text(json.dumps(dashboard_data))