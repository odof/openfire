# -*- coding: utf-8 -*-
{
    'name': u"OpenFire / Gestion des immobilisations",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Module OpenFire pour la gestion des immobilisations
===================================================
- Modifie le groupe d'accès au menu "Générer les écritures des immobilisations"

""",
    'website': "www.openfire.fr",
    'depends': [
        'account_asset',
    ],
    'data': [
        'wizards/asset_depreciation_confirmation_wizard_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
