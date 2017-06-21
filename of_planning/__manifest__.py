# -*- encoding: utf-8 -*-
{
    "name" : "OpenFire / Planning",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "website" : "http://www.openfire.fr",
    "category" : "Generic Modules/Gestion des Interventions",
    "description": """ Le module OpenFire des plannings d'intervention.
Inclut la gestion d'équipes d'intervention.""",
    "depends" : [
        'hr',
        'product',
        'sale',
        'of_base',
        'of_gesdoc',
    ],
    "init_xml" : [],
    "demo_xml" : [],
    'css' : [
        "static/src/css/of_planning.css",
    ],
    "data" : [
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
    ],
    "installable": True,
}
