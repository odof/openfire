# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenFire
#    Version OF10.0
#
#    Module conçu et développé par OpenFire SAS
#
#    Compatible avec Odoo 10 Community Edition
#
##############################################################################

{
    'name': u"OpenFire / Géolocalisation",
    'version': "10.0.1.0.0",
    'license': '',
    'author': "OpenFire",
    'website': "www.openfire.fr",
    'category': "Module OpenFlam",
    'summary': u"Géolocalisation des adresses des partenaires",
    'description': u"""
Module de Géocodage OpenFire
============================
Le module permet de géolocaliser des partenaires par géocodage (conversion d'une adresse en coordonnées GPS).

Ce module a quatre géocodeurs :
 - Serveur public national de la Base d'Adresses Nationale Ouverte
 - Serveur MapBox
Chaque géocodeur a différentes façons de déterminer la précision et de distinguer les faux positifs.

Fonctionnalités
 - Géocodage par lots, individuel ou manuel
 - Contrôle de la précision par rapport à la réponse du serveur
 - Statistiques globales recalculées dans chaque exécution en fonction des résultats déjà enregistrés
 - Statistiques par geocodeur mesurées à chaque exécution (incluant le taux de réussite)
 - Recherches et filtres pour traitement de geodonnès

Ce module nécessite la librairie mapbox : pip install mapbox
""",
    'depends': [
        'base',
        'web',
        'of_utils',
        'of_web_widgets',  # ordre des héritages FieldMany2one
    ],
    'external_dependencies': {
        'python': ['requests', 'googlemaps', 'mapbox'],
    },
    'data': [
        'wizards/of_geo_wizard_views.xml',
        'views/of_geo_views.xml',
        'views/of_geolocalize_templates.xml',
        'data/ir_config_parameters_of_geo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
