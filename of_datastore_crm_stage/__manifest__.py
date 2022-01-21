# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Connecteur CRM - Étape Kanban",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "http://www.openfire.fr",
    'category': "Openfire",
    'license': '',
    'summary': u"Openfire Connecteur commandes CRM - Étape Kanban",
    'description': u"""
Module OpenFire / Connecteur commandes CRM - Étape Kanban
=========================================================

Module permettant d'ajouter d'ajouter des infos sur les étapes kanban pour fonctionner avec le connecteur CRM
""",
    'depends': [
        'of_crm',
    ],
    'data': [
        'views/crm_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
