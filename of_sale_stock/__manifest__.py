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

- Ajout des champ "product_value_unit" et "product_value" dans "stock.inventory.line" pour le groupe Comptabilité - Gestionnaire
- Ajout du rapport "Inventaire valorisé" dans "stock.inventory.line" pour le groupe Comptabilité - Gestionnaire
- Ajout d'un filtre avancé dans les devis/bons de commandes sur la date et la date de transfert du bon de livraison
- Ajout d'une option pour afficher l'article et sa description dans le bon de livraison et les documents imprimables associés
- Ajout d'un rapport de gestion des stocks permettant de générer des fichiers Excel comprenant une liste d'article en fonction d'un ou plusieurs emplacements de stock et d'une date
- Ajout d'un champ "Route" sur les devis/bon de commandes pour remplir le champ "Route" des lignes de commandes (n'apparait que si l'option d'afficher les routes par ligne est cochée)

Paramètres de ventes
--------------------

- Description paramètre (module(s) concerné(s))
- Inhibition avertissements de stock (of_sale_kit)
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
        'report/of_sale_stock_report_templates.xml',
        'report/of_report_deliveryslip.xml',
        'security/of_sale_stock_security.xml',
        'wizard/of_report_tableur_wizard_view.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
