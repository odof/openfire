# -*- encoding: utf-8 -*-

{
        "name" : "OpenFire / Services",
        "version" : "0.1",
        "author" : "OpenFire",
        "website" : "http://www.openfire.fr",
        "category" : "Generic Modules",
        "description": """ Module OpenFire de gestion des services.""",
        "depends" : [
            'of_planning',
            'of_parc_installe',
            'of_gesdoc',
        ],
        "init_xml" : [ ],
        "demo_xml" : [ ],
        "data" : [
            'security/ir.model.access.csv',
            'views/of_service_view.xml',
            'data/of_mois_data.xml',
            'data/of_jour_data.xml',
        ],
        "installable": True,
        'active': False,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
