# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#    Copyright © 2004-2016 Odoo S.A. License GNU LGPL
#
##############################################################################

{
    'name': "OpenFire Projets - Tickets",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "projet",
    'summary': u"OpenFire Projets",
    'description': u"""
Module OpenFire Projets + Tickets
=================================
Ce module ajoute une relation entre les projets et les tickets
""",
    'depends': [
        'of_project',
        'website_support',
        ],
    'data': [
        'views/of_project_website_support_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
