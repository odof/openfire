# -*- coding: utf-8 -*-

{
    "name": "OpenFire Normes",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    'license': 'AGPL-3',
    "description": """
Normes des produits vendus OpenFire
====================================

Dans cette première version, ce module ajoute un simple champ texte dans les articles.

Prochainement, version plus complète avec intégration dans les devis/commandes/factures.
""",
    "website": "www.openfire.fr",
    "depends": ["sale"],
    "category": "OpenFire",
    "data": [
        'views/of_sale_norme_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
