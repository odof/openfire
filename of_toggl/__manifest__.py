# -*- coding: utf-8 -*-

{
    'name': u"OpenFire / Toggl",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'category': "OpenFire modules",
    'summary': u"Module de liaison Toggl",
    'license': 'LGPL-3',
    'description': u"""
Connecteur à la plateforme de saisie de temps Toggl
===========================================

Ce module permet de transmettre les pointages Toggl.
""",
    'website': "www.openfire.fr",
    'data': [
        'data/of_toggl_data.xml',
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/of_hr_timesheet_views.xml',
        'wizard/of_import_time_toggl_wizard_view.xml',
    ],
    'depends': [
        'of_hr_timesheet',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
