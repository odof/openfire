# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Portail du site internet Theme Laze",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour le portail du site internet avec le theme Laze
======================================================================
- Adaptation du module theme_laze pour fonctionner avec of_website_portal

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_website_portal',
        'theme_laze',
    ],
    'data': [
        'templates/customize_template.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
