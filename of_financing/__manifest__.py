# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Financement",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour le financement des commandes de vente
==========================================================

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_sale',
    ],
    'data': [
        'reports/sale_report_templates.xml',
        'views/sale_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
