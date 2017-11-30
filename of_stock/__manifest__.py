# -*- coding: utf-8 -*-

{
    "name": "OpenFire Stock",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'category': 'OpenFire modules',
    "description": """
Extension OpenFire du module stock
==================================

- Redéfinition template stock.report_delivery_document

""",
    "website": "www.openfire.fr",
    "depends": [
        "stock",
    ],
    "category": "OpenFire",
    "data": [
        'report/of_stock_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
