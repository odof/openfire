# -*- coding: utf-8 -*-

{
    'name': u'OpenFire / Équipement - contrats',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Équipement',
    'description': u"""
Module OpenFire pour les équipements - contrats
====================================

    """,
    'website': 'openfire.fr',
    'depends': [
        'of_equipment',
        'of_contract_custom',
        ],
    'data': [
        'views/of_equipment_contract_custom_views.xml',
        ],
    'installable': True,
    'auto_install': True,
    }
