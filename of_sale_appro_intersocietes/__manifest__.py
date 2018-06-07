# -*- coding: utf-8 -*-

{
    "name" : "OpenFire Approvisionnement intersociétés",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "description" : """
Module d'approvisionnement intersociétés
========================================
Ce module permet, lors de l'approvisionnement d'un bon de livraison, de choisir d'effectuer l'achat de marchandises
auprès d'une autre société de la même base.
Cette action génère une demande de prix pour la société courante et un devis auprès de la seconde société.

Les conditions d'approvisionnement intersociétés sont gérées par des règles à créer dans la configuration des achats.

Bon de livraison:
-----------------

- Ajout d'un bouton pour l'approvisionnement intersociétés (crée une commande client pour la société fournisseur et une commande fournisseur pour la société cliente)

Configuration achats:
---------------------

- Ajout d'un menu pour créer les règles d'approvisionnement intersociétés
""",
    "website" : "www.openfire.fr",
    "depends" : ["sale", "of_sale_appro", "stock", "of_base"],
    "category" : "OpenFire",
    "license": "",
    "data" : [
        'views/of_sale_appro_rule_view.xml',
        'wizards/of_appro_intersocietes_wizard_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
