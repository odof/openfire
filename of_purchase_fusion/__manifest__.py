# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#
##############################################################################

{
    'name': u"OpenFire / Fusion commandes fournisseur",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'license': '',
    'summary': u"Openfire Fusion des commandes fournisseurs",
    'description': u"""
Module OpenFire / Fusion des commandes fournisseur
==================================================
Modifications OpenFire pour les commandes fournisseur

Fonctionnalités
---------------
- Ajout de la possibilité de fusionner des commandes fournisseurs avec d'autres commandes d'un même fournisseur
- Ajout d'un smart button vers les commandes clients liées depuis la commande fournisseur
- Ajout d'un champ 'Commandes liées' sur les commandes fournisseurs
- Ajout du client sur les lignes des commandes fournisseurs (livraison attendue également mais uniquement en DB)
- Modifications de l'impression 'Commande fournisseur' (ajout contremarque sur les lignes)
""",
    'depends': ['of_purchase', 'of_sale'],
    'data': [
        'wizards/of_fusion_commande_fournisseur_view.xml',
        'views/of_purchase_fusion_view.xml',
        'report/of_purchase_fusion_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
