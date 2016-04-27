# -*- coding: utf-8 -*-

{
    "name" : "OpenFire Calendar",
    "version" : "1.1",
    "author" : "OpenFire",
    'complexity': "easy",
    "description" : """
Désactivation de l'option drag-and-drop de la vue calendrier
""",
    "website" : "www.openfire.fr",
    "category" : "OpenFire",
    "sequence": 100,
    "depends" : ['web_calendar'],
    "init_xml" : [
    ],
    "data" : [
        'views/of_calendar_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
