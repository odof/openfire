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

Module de lien entre of_sale et of_planning :
    - Ajoute la gestion estimative des temps de pose pour les devis/commandes

""",
    'depends': [
        'of_sale',
        'of_sale_report',
        'of_planning',
    ],
    'data': [
        'views/of_sale_planning_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
