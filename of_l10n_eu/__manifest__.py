# -*- coding: utf-8 -*-

{
    'name': 'OpenFire / Implémentation obligations légales en Europe',
    'author': 'OpenFire',
    'version': '10.0.1.0.0',
    'category': 'OpenFire modules',
    'summary': 'Obligations légales Européenne',
    'license': '',
    'description': """
Module qui implèmente les obligations légales en Europe :

- Ajout des champs nécessaires pour être conforme aux règles de la RGPD (opt-out, date d'autorisation, type d'autorisation)
    """,
    'website': 'openfire.fr',
    'depends': [
        'mail',
        ],
    'data': [
        'views/rgpd_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
