# -*- coding: utf-8 -*-

{
    "name": "OpenFire Sale Stock",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'category': 'OpenFire modules',
    "description": """
Extension OpenFire du module sale_stock
=======================================

- Ajout du champ 'product_value' dans 'stock.inventory.line' pour le groupe Comptabilité - Gestionnaire
- Ajout du rapport "Inventaire valorisé" dans 'stock.inventory.line' pour le groupe Comptabilité - Gestionnaire
- Ajout d'un filtre avancé dans les devis/bons de commandes sur la date et la date de transfert du bon de livraison

Paramètres de Ventes (sale.config.settings)
-------------------------------------------

- description paramètre (module(s) concerné(s))
- inhibition avertissements de stock (of_sale_kit)
""",
    "website": "www.openfire.fr",
    "depends": [
        "sale_stock",
        "of_sale",
    ],
    "category": "OpenFire",
    "data": [
        'views/of_sale_stock_views.xml',
        'report/of_report_stockinventory_valued.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
