# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Gestion électronique des documents - Site web",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "OpenFire",
    'description': u"""
Module OpenFire de gestion électronique des documents pour le site web
======================================================================

Ce module permet la diffusion de documents présents dans la GED sur le site internet
""",
    'depends': [
        'of_document',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/of_document_website_security.xml',
        'views/dms_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
