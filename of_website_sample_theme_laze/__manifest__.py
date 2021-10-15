# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Gestion des échantillons Theme Laze",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour e-commerce : Gestion des échantillons avec le theme Laze
=============================================================================
- Adaptation du module theme_laze pour fonctionner avec of_website_sample

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_website_sample',
        'theme_laze',
    ],
    'data': [
        'templates/website_sale.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
