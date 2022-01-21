# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#
##############################################################################

{
    'name' : u"OpenFire / Ventes / eCommerce",
    'version' : "10.0.1.0.0",
    'license': '',
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Module OpenFlam",
    'summary': u"Module intermédiaire ventes/ecommerce OpenFire",
    'description': u"""

Module OpenFire intermédiaires entre of_sale et of_website_sale
========================
""",
    'depends' : [
        "of_sale",
        "of_website_sale",
    ],
    'data' : [
        'views/of_sale_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}