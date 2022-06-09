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
    'name': u"OpenFire / Ventes - planning",
    'version': "10.0.1.0.0",
    'license': '',
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Module OpenFlam",
    'summary': u"Personnalisation des ventes OpenFire",
    'description': u"""

Module OpenFire / Ventes - planning
===================================

Module de lien entre of_sale et of_planning permettant la facturation sur quantités plafiniées depuis une commande.
    - Ajoute la gestion estimative des temps de pose pour les devis/commandes.
""",
    'depends': [
        'of_sale',
        'of_planning',
        'of_sale_report',
        'of_sale_quote_template_kit',
        ],
    'external_dependancies': {
        'python': ['pdfminer', 'pypdftk', 'pyPdf'],
    },
    'data': [
        'views/of_sale_planning_views.xml',
        'views/stock_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
