# -*- coding: utf-8 -*-

{
    'name' : u"OpenFire - Personnalisation du module Odoo feuilles de temps",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': u"Module OpenFire - Employés",
    'complexity': "",
    'summary': u"Personnalisation du module Odoo feuilles de temps",
    'description': u"""
Module OpenFire - Personnalisation du module Odoo feuilles de temps
===================================================================

- Ajout des catégories dans les feuilles de temps et les activités détaillées
""",
    'depends' : [
        'hr_timesheet',
        'hr_timesheet_sheet',
    ],
    'data' : [
        'views/of_hr_timesheet_views.xml',
        'security/ir.model.access.csv',
    ],
    'active': True,
    'installable': True,
    'application': False,
    'auto_install': False,
}