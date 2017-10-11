# -*- coding: utf-8 -*-

{
    "name": "OpenFire Sale",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    'category': 'OpenFire modules',
    "description": """
Personnalisation des ventes OpenFire
====================================

Modification de l'affichage du formulaire de devis/commande client.
Refonte de report.report_saleorder_document

Ajout d'un filtre de recherche pour les commandes à facturer entièrement.
Report de la description fabricant dans les devis et factures.

Paramètres de Ventes (sale.config.settings)
-------------------------------------------

- description paramètre (module(s) concerné(s))
- inhibition avertissements de stock (of_sale_kit)
- inhibition affichage réf produit dans les rapports PDF (of_sale)
""",
    "website": "www.openfire.fr",
    "depends": [
        "sale",
        "of_product",
        "of_base",
    ],
    "category": "OpenFire",
    "data": [
        'views/of_sale_view.xml',
        'report/of_sale_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
