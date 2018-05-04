# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS sous licence AGPL-3.0
#
#    Compatible avec Odoo 10 Community Edition
#    Copyright © 2004-2016 Odoo S.A. License GNU LGPL
#
##############################################################################

{
    'name' : "OpenFire - Planning",
    'version' : "10.0.1.0.0",
    'license': 'AGPL-3',
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Generic Modules / Gestion des Interventions",
    'summary': u"Planification des interventions",
    'description': u"""
Module OpenFire - Plannings d'intervention
==========================================
Le module OpenFire des plannings d'intervention.
Inclut la gestion d'équipes d'intervention.

Fonctionnalités
----------------

""",
    'depends' : [
        'hr',
        'product',
        'sale',
        'of_base',
        'of_gesdoc',
        'of_calendar',
        'of_kit',
        #'of_map_view',
    ],
    'external_dependancies': {
        #'python': ['pypackage1', 'pypackage2'],
    },
    'data' : [
        'security/of_planning_security.xml',
        'security/ir.model.access.csv',
        # 'wizard/wizard_calendar.xml',
        # 'of_planning_view.xml',
        # 'of_planning_data.xml',
        # 'wizard/wizard_print_pose.xml',
        # 'wizard/wizard_print_res.xml',
        # 'wizard/wizard_equipe_semaine.xml',
        # 'of_planning_report.xml',
        'wizard/message_invoice.xml',
        'views/of_planning_intervention_view.xml',
        'views/of_planning_report_view.xml',
        # 'wizard/of_planning_pose_mensuel_view.xml',
        'report/of_planning_fiche_intervention_view.xml',
        'report/of_planning_report_templates.xml',
    ],
    'demo': [],
    'demo_xml' : [],
    'init_xml' : [],
    'css' : [
        'static/src/css/of_planning.css',
    ],
    'qweb': [
        #'static/src/xml/*.xml',
    ],
    'active': True,
    'installable': True,
    'application': False,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:sorderttabstop=4:shiftwidth=4:
