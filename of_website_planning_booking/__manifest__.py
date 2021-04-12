# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Prise de RDV en ligne",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': u"Prise de RDV en ligne",
    'license': 'LGPL-3',
    'description': u"""
Module OpenFire pour la prise de RDV en ligne depuis le site internet
=====================================================================

Fonctionnalités additionnelles :
------------------------------
    - Ajout de la liste des parcs installés sur le portail utilisateur.
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_planning_tournee',
        'of_website_portal',
        'of_parc_chem',
        'auth_signup',
    ],
    'data': [
        'data/of_website_planning_booking_data.xml',
        'views/of_website_planning_booking_views.xml',
        'views/of_website_planning_booking_templates.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': False,
}
