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
    'name' : u"OpenFire / Ventes - planning",
    'version' : "10.0.1.0.0",
    'license': '',
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Module OpenFlam",
    'summary': u"Personnalisation des ventes OpenFire",
    'description': u"""

Module OpenFire / Ventes - planning
========================

""",
    'depends' : [
        "of_sale",
        "of_planning",
        ],
    'external_dependancies': {
        'python': ['pdfminer', 'pypdftk', 'pyPdf'],
    },
    'data' : [
        # 'views/of_sale_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
