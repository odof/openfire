# -*- coding: utf-8 -*-

{
    'name': 'OpenFire Nomenclature',
    'author': 'OpenFire',
    'version': '10.0',
    'category': 'OpenFire modules',
    'summary': 'Nomenclatures',
    'description': """
Module de Nomenclatures openfire:
=================================

config des nomenclature depuis ventes/configuration/articles
    """,
    'website': 'openfire.fr',
    'depends': [
        'of_sale',
        ],
    'data': [
        'wizard/gf_nomenclature_wizard_views.xml',
        'views/gf_nomenclature_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
