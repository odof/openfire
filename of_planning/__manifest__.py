# -*- encoding: utf-8 -*-
{
        "name" : "OpenFire / Planning",
        "version" : "0.9",
        "author" : "OpenFire",
        "website" : "http://www.openfire.fr",
        "category" : "Generic Modules/Gestion Pose",
        "description": """ Le module OpenFire des plannings de pose.
Inclut la gestion d'équipes de pose.""",
        "depends" : [
                     'hr',
                     'product',
#                      'of_calendar',
                     'of_base',
                     ],
        "init_xml" : [ ],
        "demo_xml" : [ ],
        'css' : [
            "static/src/css/of_planning.css",
        ],
        "data" : [
            'security/of_planning_security.xml',
            'security/ir.model.access.csv',
#             'wizard/wizard_calendar.xml',
#             'of_planning_view.xml',
#             'of_planning_data.xml',
#             'wizard/wizard_print_pose.xml',
#             'wizard/wizard_print_res.xml',
#             'wizard/wizard_equipe_semaine.xml',
#             'of_planning_report.xml',
#             'wizard/message_invoice.xml',
            'views/of_planning_pose_view.xml',
#            'wizard/of_planning_pose_mensuel_view.xml',
        ],
        "installable": True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
