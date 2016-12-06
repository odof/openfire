# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
        "name" : "OpenFire / Module gestion de prêt d'appareils",
        "version" : "1.1",
        "author" : "OpenFire",
        "website" : "www.openfire.fr",
        "category" : "OpenFire",
        "description": """
Module gestion de prêt d'appareils
""",
        "depends" : [
            'project',
            'of_sav_but'
        ],
        "demo_xml" : [ ],
        "data" : [
            'views/of_pret_appareil_view.xml',
        ],
        "installable": True,
        'active': False,
}

