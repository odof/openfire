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
    'name': u"OpenFire / Sous-traitance",
    'version': "10.0.1.0.0",
    'license': '',
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'summary': u"Gestion de la sous-traitance OpenFire",
    'description': u"""
Module OpenFire / Sous-traitance
================================

- Ajoute la notion de sous-traitance sur les lignes de commande
""",
    'depends': [
        'subcontracted_service',
        'of_sale',
        'of_sale_stock',
    ],
    'data': [
        'views/of_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
