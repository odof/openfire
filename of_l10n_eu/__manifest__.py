# -*- coding: utf-8 -*-

{
    'name': 'OpenFire / Implémentation obligations légales en Europe',
    'author': 'OpenFire',
    'version': '10.0.1.0.0',
    'category': 'OpenFire modules',
    'summary': 'Obligations légales européennes',
    'license': '',
    'description': """
Module qui implèmente les obligations légales en Europe :

- Partenaires : ajout des champs d'autorisation d'utilisation des données personnelles (RGPD)
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
