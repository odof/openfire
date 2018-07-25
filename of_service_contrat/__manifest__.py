# -*- coding: utf-8 -*-

{
    'name' : "OpenFire Contrat de service",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "http://www.openfire.fr",
    'category' : "Generic Modules",
    'license': '',
    'description': """ Module OpenFire de gestion des services.""",
    'depends' : [
        'of_service',
        'of_gesdoc',
    ],
    'init_xml' : [],
    'demo_xml' : [],
    'data' : [
        'views/of_service_contrat_view.xml',
    ],
    'installable': True,
}
