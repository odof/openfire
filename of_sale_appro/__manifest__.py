# -*- coding: utf-8 -*-

{
    "name": "OpenFire / Approvisionnement ventes",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    "description" : """

Bon de livraison client :

- Ajout d'un bouton sur lignes pour demande d'approvisionnement
- Ajout d'un bouton pour approvisionner toutes les lignes en même temps (si elles peuvent l'être)
- Ajout des colonnes quantité stock et quantité prévisionnelle dans onglet "Demande initiale"
""",
    "website": "www.openfire.fr",
    'license': '',
    "depends": [
        'of_sale',
        'stock',
        'of_base',
    ],
    "category": "OpenFire",
    "data": [
        'views/of_sale_appro_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
