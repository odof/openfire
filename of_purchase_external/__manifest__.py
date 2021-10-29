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
    'name' : u"OpenFire / Achats - En-tête et pied de page personnalisés",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Purchases",
    'summary': u"OpenFire Purchases",
    'description': u"""
Module OpenFire / Achats - En-tête et pied de page personnalisés
================================================================
Module de lien entre les achats et en-tête/pied de page personnalisés OpenFire

Fonctionnalités
----------------
- Ajoute le nom du document sur les commandes d'achats suivant une option sur la société.

""",
    'depends' : [
        'of_purchase',
        'of_external',
    ],
    'data' : [
        'report/purchase_order.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
