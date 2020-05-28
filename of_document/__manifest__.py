# -*- coding: utf-8 -*-

{
    'name': "OpenFire / Gestion électronique des documents",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': 'Gestion électronique des documents',
    'description': u"""
Module OpenFire pour la gestion électronique des documents
==========================================================

 - XXX
""",
    'depends': [
        'muk_dms',
        'muk_web_preview_attachment',
        'muk_web_preview_image',
        'sale',
        'purchase',
        'account',
        'stock',
        'crm',
        'project',
        'of_service',
        'of_base',
    ],
    'data': [
        'data/of_document_data.xml',
        'views/dms_views.xml',
        'views/partner_views.xml',
        'views/of_document_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
