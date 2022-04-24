# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Connecteur Odoo",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Openfire",
    'description': u"""
Module OpenFire de connexion à une base Odoo.
=============================================

Ajout d'une classe abstraite permettant de se connecter à une autre base odoo.
""",
    'depends': [
        'of_base'
    ],
    'external_dependencies': {
        'python': [
            'openerplib'
        ],
    },
    'init_xml': [],
    'demo_xml': [],
    'data': [],
    'installable': True,
}
