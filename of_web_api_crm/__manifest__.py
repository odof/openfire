# -*- coding: utf-8 -*-

{
    'name': "OpenFire / API (CRM)",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': '',
    'complexity': "easy",
    'description': u"""
Module d'API web OpnFire - CRM
==============================

Vérification pour ne pas créer de doublons de contacts à la création d'opportunités.

Autorisation d'accès par l'API aux opportunités et un certain nombre de leurs champs.

""",
    'website': "www.openfire.fr",
    'depends': [
        'of_web_api',
        'of_crm',
    ],
    'category': "OpenFire",
    'data': [
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
