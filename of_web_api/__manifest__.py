# -*- coding: utf-8 -*-

{
    'name': "OpenFire / API",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': '',
    'complexity': "easy",
    'description': u"""
Module d'API web OpnFire
========================

Création d'un utilisateur API pour effectuer des actions automatisées.

/!\ Pour des raisons de sécurité, il est nécessaire de configurer le mot de passe de l'utilisateur API depuis l'interface.

Les modèles et leurs champs ont désormais une case à cocher 'of_api_auth' qui défini si l'API peut intervenir dessus.


Fonctionnalités de l'API
------------------------

Création d'enregistrements

""",
    'website': "www.openfire.fr",
    'depends': [
        'base',
        'of_l10n_eu_mass_maling',  # champs RGPD dans res.partner
        'of_geolocalize',  # champs de géoloc dans res.partner
    ],
    'category': "OpenFire",
    'data': [
        'data/of_web_api_data.xml',
        'views/of_web_api_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
