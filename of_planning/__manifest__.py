# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
    'name': u"OpenFire / Planning",
    'version': '10.0.1.2.0',
    'author': u"OpenFire",
    'website': u"www.openfire.fr",
    'category': u"Generic Modules",
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
        'of_stock',
        'l10n_fr_department',
    ],
    'data': [
        'security/of_planning_security.xml',
        'security/ir.model.access.csv',
        'report/of_planning_fiche_intervention.xml',
        'report/of_planning_fiche_intervention_view.xml',
        'report/of_planning_report_templates.xml',
        'report/of_planning_rapport_intervention.xml',
        'data/data.xml',
        'wizard/message_invoice.xml',
        'views/of_planning_intervention_view.xml',
        'views/of_res_config_views.xml',
        'views/of_planning_report_view.xml',
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
