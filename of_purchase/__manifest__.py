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
    'name' : u"OpenFire Purchase",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Purchases",
    'summary': u"OpenFire Purchases",
    'description': u"""
Module OpenFire - Purchase
==========================
Modifications OpenFire pour les commandes fournisseur

Fonctionnalités
----------------
- Ajout de la date souhaitée de livraison (champ texte) pour les commandes client et fournisseur
- Ajout du client final dans les commandes fournisseur, auto-alimenté depuis la commande client
- Modification des documents imprimés pour l'ajout de ces informations
- Ajout de l'impression de la commande fournisseur sans prix
- Ajout option pour afficher la description telle que saisie dans le devis dans la commande fournisseur et les documents imprimables associés
- Ajoute un smart button vers les commandes fournisseurs liées depuis le bon de commande

""",
    'depends' : [
        'purchase',
        'sale',
    ],
    'data' : [
        'report/purchase_report_templates.xml',
        'report/purchase_reports.xml',
        'views/of_purchase_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
