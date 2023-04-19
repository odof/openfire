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
    'name': u"OpenFire / Ventes - vue kanban",
    'version': "10.0.1.0.0",
    'license': '',
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Module OpenFlam",
    'summary': u"Personnalisation des ventes OpenFire",
    'description': u"""

Module OpenFire / Ventes - vue kanban
=====================================

Modification de la vue kanban des devis/commandes + ajout d'un champ étapes kanban

""",
    'depends': [
        'sale',
        'of_crm'
    ],
    'external_dependencies': {
        'python': ['pdfminer', 'pypdftk', 'pyPdf'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/of_sale_kanban_view.xml',
        'views/of_sale_kanban_templates.xml',
        'data/of_sale_kanban_data.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
