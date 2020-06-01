# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Module Parrainage",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module Parrainage : gestion des parrainages sur opportunités
""",
    'depends': [
        'of_crm',
    ],
    'data': [
        'views/of_parrainage_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
