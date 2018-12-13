# -*- encoding: utf-8 -*-

{
    "name" : "OpenFire / Planning des tournées",
    "version" : "10.0.1.0.0",
    "author" : "OpenFire",
    "website" : "http://www.openfire.fr",
    "category" : "Generic Modules/Gestion des interventions",
    "description": """ Gestion des tournées
     - Planification RDV dans Planning Intervention
     - RDV pour les clients
     - Recherche géolocalisée des clients (Adresse Livraison)""",
    "depends" : [
        'of_planning',
        'of_service',
        'of_geolocalize',
        'of_map_view',
        # 'of_gesdoc',
        # 'of_imports',
        'of_base_location',
    ],
    "init_xml" : [],
    "demo_xml" : [],
    "data" : [
        'security/ir.model.access.csv',
        # 'wizard/add_partner_view.xml',
        'wizard/rdv_view.xml',
        'wizard/planification_view.xml',
        # 'wizard/search_partner_view.xml',
        # 'wizard/impression_view.xml',
        'views/of_planning_tournee_view.xml',
        # 'of_planning_res_report.xml',
        # 'data/of_imports_prechamp_client.xml',
    ],
    "installable": True,
}
