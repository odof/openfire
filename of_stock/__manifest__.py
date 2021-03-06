# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Stock",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'category': 'OpenFire',
    "description": """
Extension OpenFire du module stock
==================================

- Possibilité de sélectionner le même article plusieurs fois dans le même inventaire. Les quantités seront cumulées.
- Ajout de l'id (non modifiable) et d'un champ note dans les lignes d'inventaire.
- Édition des lignes d'inventaire par le haut.
""",
    "website": "www.openfire.fr",
    "depends": [
        "stock",
    ],
    "data": [
        'views/of_stock_views.xml',
        'wizards/of_stock_date_confirmation_views.xml',
        'wizards/stock_backorder_confirmation_views.xml',
        'wizards/stock_immediate_transfer_views.xml',
        'wizards/of_specific_delivery_report_wizard_views.xml',
        'reports/of_specific_delivery_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
