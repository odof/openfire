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

Pour faire l'import, aller dans Configuration -> Technique -> Cities/Locations Management -> importer de Geonames
""",
    'author': "OpenFire",
    'website': 'http://www.akretion.com',
    'depends': [
        'of_base',
        'base_location_geonames_import',
        'l10n_fr_base_location_geonames_import',  # Dépendance inutile pour le module. Sert uniquement à ne pas oublier d'installer ce module
    ],
    'data': [
        'views/of_better_zip_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
