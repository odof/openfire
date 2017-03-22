# -*- coding: utf-8 -*-

{
    'name': 'OpenFire / Géolocalisation des communes',
    'version': '10.0.1.0.0',
    'category': 'Extra Tools',
    'license': 'AGPL-3',
    'summary': 'Coordonnées GPS des villes et lieux',
    'description': """
Ajout des coordonnées GPS à la structure des villes importées

Nécessite l'installation du module base_location_geonames_import du dépôt partner-contact de l'OCA.
""",
    'author': "OpenFire",
    'website': 'http://www.akretion.com',
    'depends': ['base_location_geonames_import'],
    'data': [
        'views/of_better_zip_view.xml',
    ],
    'installable': True,
}
