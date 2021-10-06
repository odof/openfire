# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Portail du site internet Theme Impacto",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour le portail du site internet avec le theme Impacto
======================================================================
- Adaptation du module theme_impacto pour fonctionner avec of_website_portal

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_website_portal',
        'theme_impacto',
    ],
    'data': [
        'templates/customize_modal_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
