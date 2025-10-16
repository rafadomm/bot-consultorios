# mano_de_obra_queries.py

import baserow_queries
import config

def get_paid_workers():
    """Obtiene una lista única de trabajadores desde la tabla de PAGOS."""
    all_payments = baserow_queries._get_all_rows_paginated(config.ID_TABLA_PAGOS_MO)
    if all_payments is None:
        return []

    workers = set()
    for row in all_payments:
        if row.get('TRABAJADOR'):
            workers.add(row['TRABAJADOR']['value'])
    
    return sorted(list(workers))

def get_payments_by_worker(worker_name):
    """Obtiene todos los pagos para un trabajador específico desde la tabla de PAGOS."""
    all_payments = baserow_queries._get_all_rows_paginated(config.ID_TABLA_PAGOS_MO)
    if all_payments is None:
        return []

    worker_payments = []
    for row in all_payments:
        if row.get('TRABAJADOR') and row['TRABAJADOR']['value'] == worker_name:
            worker_payments.append(row)
            
    return worker_payments

