# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
        "name" : "OpenFire / Module spécifique pour Nile",
        "version" : "1.1",
        "author" : "OpenFire",
        "website" : "www.openfire.fr",
        "category" : "OpenFire",
        "description": """
Module spécifique pour Nile

- Ajout/modification champs/menus spécifiques pour Nile
""",
        "depends" : [
            'hr_timesheet',
            'hr_timesheet_sheet',
        ],
        "demo_xml" : [ ],
        "data" : [
            'security/ir.model.access.csv',
            'of_zz_nile_view.xml',
        ],
        "installable": True,
        'active': False,
}
# vim:expandtab:smartindent:tabstop=4:sorderttabstop=4:shiftwidth=4:
