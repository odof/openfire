# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#
##############################################################################

{
    'name' : u"OpenFire / Personnalisation du module Odoo feuilles de temps",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': u"OpenFire",
    'complexity': "",
    'summary': u"Personnalisation du module Odoo feuilles de temps",
    'description': u"""
Ce module personnalise le module Odoo des feuilles de temps.
============================================================

- Ajout des catégories dans les feuilles de temps et les activités détaillées
- Ajout des filtres de recherche personnalisés aux feuilles de temps.
""",
    'depends' : [
        'hr_timesheet',
        'hr_timesheet_sheet',
    ],
    'data' : [
        'views/of_hr_timesheet_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}