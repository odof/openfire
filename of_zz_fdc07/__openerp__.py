# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
        "name" : "OpenFire / Module spécifique pour FDC07",
        "version" : "1.1",
        "author" : "OpenFire",
        "website" : "www.openfire.fr",
        "category" : "OpenFire",
        "description": """
Module spécifique pour FDC07

- Ajout/modification champs/menus spécifiques pour FDC 07
""",
        "depends" : [
            'of_base',
            'calendar',
            'hr',
            'hr_timesheet_sheet',
            'hr_holidays',
        ],
        "demo_xml" : [ ],
        "data" : [
            #'security/ir.model.access.csv',
            'of_zz_fdc07_view.xml',
        ],
        "installable": True,
        'active': False,
}
# vim:expandtab:smartindent:tabstop=4:sorderttabstop=4:shiftwidth=4:
