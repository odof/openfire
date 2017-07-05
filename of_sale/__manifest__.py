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

Ajout d'un filtre de recherche pour les commandes à facturer entièrement.
Report de la description fabricant dans les devis et factures.
""",
    "website": "www.openfire.fr",
    "depends": ["sale","of_product"],
    "category": "OpenFire",
    "data": [
        'views/of_sale_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
