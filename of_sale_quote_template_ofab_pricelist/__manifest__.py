# -*- coding: utf-8 -*-

{
    'name': "OpenFire / Modèle de devis / Liste de prix",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Module Fabricants OpenFire",
    'summary': u"Module intermédiaire Liste de prix et Modèle de devis",
    'description': u"""
Module OpenFire / Modèle de devis / Liste de prix
=================================================
Module intermédiaire Liste de prix et Modèle de devis
""",
    'depends': [
        'of_sale_quote_template',
        'ofab_pricelist',
    ],
    'data': [
        'views/ofab_pricelist_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
