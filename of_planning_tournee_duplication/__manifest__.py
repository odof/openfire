# -*- encoding: utf-8 -*-

{
    "name": u"OpenFire / Planning des tournées",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    "website": "http://www.openfire.fr",
    "category": "Generic Modules/Gestion des interventions",
    "description": u"""Gestion des tournées
     - Planification RDV dans Planning Intervention
     - RDV pour les clients
     - Recherche géolocalisée des clients (Adresse Livraison)""",
    "depends": [
        'of_planning_tournee',
        'of_service',
        'of_geolocalize',
        'of_map_view',
        'of_base_location',
        'of_sale',
        ],
    "init_xml": [],
    "demo_xml": [],
    "data": [
        'data/data.xml',
        'wizards/duplication_views.xml',
        ],
    "installable": True,
    }
