# -*- encoding: utf-8 -*-

{
    'name' : "OpenFire / Services",
    'version' : "0.1",
    'author' : "OpenFire",
    'website' : "http://www.openfire.fr",
    'category' : "Generic Modules",
    'description': """ Module OpenFire de gestion des services.""",
    'depends' : [
        'of_planning',
        'of_map_view',
        'of_utils',
    ],
    'init_xml' : [],
    'demo_xml' : [],
    'data' : [
        'security/ir.model.access.csv',
        'views/of_service_view.xml',
    ],
    'installable': True,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
