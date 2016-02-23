# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
        "name" : "OpenFire / Module spécifique pour Win",
        "version" : "1.1",
        "author" : "OpenFire",
        "website" : "www.openfire.fr",
        "category" : "OpenFire",
        "description": """
Module spécifique pour Win

- Affichages personnalisés pour Win
""",
        "depends" : [
            'of_project_issue',
            'of_planning',
            'of_parc_installe',
            'product',
        ],
        "demo_xml" : [ ],
        "data" : [
            'security/ir.model.access.csv',
            'of_zz_winterhalter_view.xml',
        ],
        "installable": True,
        'active': False,
}
# vim:expandtab:smartindent:tabstop=4:sorderttabstop=4:shiftwidth=4:
