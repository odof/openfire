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
    'name': u"OpenFire / Analyse Retail",
    'version': "10.0.1.0.0",
    'license': '',
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Module OpenFlam",
    'summary': u"Analyse Retail",
    'description': u"""

Module OpenFire / Analyse Retail
================================

Module ajoutant des champs de qualification au niveau des sociétés destinés à affiner l'analyse des performances 
économiques par groupe de société.
 
""",
    'depends': [
        'of_base',
        'sale',
        'ks_dashboard_ninja',
        'of_crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/company_views.xml',
        'views/assets_views.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
