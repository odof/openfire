# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Portail du site internet - État de stock de combustible",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour l'état de stock de combustible sur le portail du site internet
===================================================================================

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_partner_fuel_stock',
        'website_portal',
    ],
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
