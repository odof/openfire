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
    'name': u"OpenFire / Générateur de données de démo",
    'version': '10.0.1.0.0',
    'license': '',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "Module OpenFire",
    'summary': u"Générateur de données de démo",
    'description': u"""
""",
    'depends': [
        'of_base',
        'of_sale',
        'of_planning',
    ],
    'data': [
        'wizards/wizard_demo_dara_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
