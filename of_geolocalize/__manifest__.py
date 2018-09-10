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
    'name' : u"OpenFire Géolocalisation",
    'version' : "10.0.1.0.0",
    'license': '',
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category': "Module OpenFlam",
    'summary': u"Géolocalisation des partenaires",
    'description': u"""
Module de Géocodage OpenFire
============================
Le module permet de géolocaliser des partenaires par géocodage (conversion d'une adresse en coordonnées GPS).

Ce module a quatre géocodeurs :
 - Serveur Nominatim dédié de la société OpenFire
 - Severur Nominatim public d'OpenStreetMap
 - Serveur public national de la Base d'Adresses Nationale Ouverte
 - Serveur public de Google Maps (d'abord une requête web anonyme, puis avec la clé API d'OpenFire ou un autre)
Chaque géocodeur a différentes façons de déterminer la précision et de distinguer les faux positifs.

Fonctionnalités
 - Géocodage par lots, individuel ou manuel
 - Contrôle de la précision par rapport à la réponse du serveur (différents algorithmes)
 - Contrôle des faux positifs comparant la requête envoyée avec la réponse du serveur (différents filtres)
 - Possibilité de choisir la meilleure précision des différents géocodeurs utilisés (cela prend plus de temps)
 - Statistiques globales recalculées dans chaque exécution en fonction des résultats déjà enregistrés 
 - Statistiques par geocodeur mesurées à chaque exécution (incluant le taux de réussite)
 - Paramétrage pour l'APIs, l'URLs de geocodeurs et des fonctions automatiques de géocodage
 - Recherches et filtres pour traitement de geodonnès

""",
    'depends' : [
        'base',
    ],
    'external_dependancies': {
        'python': ['requests', 'googlemaps',],
    },
    'data' : [
        'wizards/of_geo_wizard_views.xml',
        'views/of_geo_views.xml',
        'data/ir_config_parameters_of_geo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
