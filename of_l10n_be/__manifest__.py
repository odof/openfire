# -*- coding: utf-8 -*-

{
    'name': 'OpenFire / Comptabilité belge',
    'author': 'OpenFire',
    'version': '10.0.1.0.0',
    'category': 'OpenFire modules',
    'summary': 'Comptabilité spéciale Belgique',
    'license': '',
    'description': """
Module qui implémente les régles comptable spécifiques à la Belgique :

Configuration Comptabilité :
 - ajout de taxes des services par défauts pour vente/achat
    """,
    'website': 'openfire.fr',
    'depends': [
        'of_sale',
        ],
    'data': [
        'views/of_l10n_be_views.xml',
        ],
    'installable': True,
    'auto_install': False,
}
