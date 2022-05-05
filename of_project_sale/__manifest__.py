# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#    Copyright © 2004-2016 Odoo S.A. License GNU LGPL
#
##############################################################################

{
    'name': "OpenFire Projets Ventes",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "projet",
    'summary': u"OpenFire Projets Ventes",
    'description': u"""
Module OpenFire Projets Ventes
==============================
Ce module modifie/ajoute des fonctionnalités aux projets

Modifications
-------------
- Ajoute un modèle de tâche aux articles
- Permet de créer un projet et des tâches à la validation d'une commande client
""",
    'depends': [
        'of_project',
        'of_purchase',
        'of_sale',
        'sales_team',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/task_template_views.xml',
        'views/product_views.xml',
        'views/project_views.xml',
    ],
    'demo': [
    ],
    'application': False,
    'installable': True,
}
