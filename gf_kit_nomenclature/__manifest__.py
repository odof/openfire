# -*- coding: utf-8 -*-

{
    'name': 'OpenFire Kit Nomenclature',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Nomenclatures et kits',
    'description': """
Module de Nomenclatures avec kits openfire:
===========================================

implémentation des kits dans les nomenclatures

@TODO: reprendre l'architechture des kits pour le wizard d'insert nomenclature
    """,
    'website': 'openfire.fr',
    'depends': [
        'gf_nomenclature',
        'of_kit',
        ],
    'data': [
        'wizard/gf_kit_nomenclature_wizard_views.xml',
        'views/gf_kit_nomenclature_views.xml',
    ],
    'installable': True,
    'auto_install': True,  # auto-installé si kits + nomenclatures
}
