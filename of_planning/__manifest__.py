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
    'name': "OpenFire / Planning",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Generic Modules",
    'summary': u"Gestion des interventions",
    'description': u"""
Module OpenFire / Planning
==========================

Module OpenFire des plannings d'intervention.
Inclut la gestion des équipes d'intervention.

""",
    'depends': [
        #'hr',  # par of_calendar
        'product',
        'sale',
        #'of_base', par of_base_location
        'of_gesdoc',
        'of_calendar',
        'of_kit',
        'mail',
        'of_utils',
        'of_base_location',  # secteurs
        'stock',
    ],
    'data': [
        'security/of_planning_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'wizard/message_invoice.xml',
        'views/of_planning_intervention_view.xml',
        'views/of_res_config_views.xml',
        'views/of_planning_report_view.xml',
        'report/of_planning_fiche_intervention.xml',
        'report/of_planning_fiche_intervention_view.xml',
        'report/of_planning_report_templates.xml',
        'report/of_planning_rapport_intervention.xml',
        'views/of_planning_intervention_template_views.xml',
    ],
    'css': [
        'static/src/css/of_planning.css',
    ],
    'qweb': [
        'static/src/xml/of_planning_calendar_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
