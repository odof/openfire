# -*- coding: utf-8 -*-

{
    'name': u'OpenFire / Équipement',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Équipement',
    'description': u"""
Module OpenFire pour les équipements
====================================

    """,
    'website': 'openfire.fr',
    'depends': [
        'maintenance',
        'of_planning_tournee',
        ],
    'data': [
        'security/ir_rules.xml',
        'views/of_equipment_views.xml',
        'views/ir_ui_menus_views.xml',
        ],
    'installable': True,
    'auto_install': False,
    }
