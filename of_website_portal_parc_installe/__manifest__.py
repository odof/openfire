# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Portail du site internet - Parc installé",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour le parc installé sur le portail du site internet
=====================================================================

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_parc_installe',
        'website_portal',
    ],
    'data': [
        'views/of_website_portal_parc_installe_templates.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
