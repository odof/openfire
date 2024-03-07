# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Vue carte pour les équipement",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Ajout de la vue carte (OpenStreetMap) pour les équipements",
    'depends': [
        'of_equipment',
        'of_map_view',
    ],
    'data': ['views/of_equipment_views.xml'],
    'assets': {
        'web.assets_backend': [
            '/of_map_view_equipment/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': True,
    'uninstall_hook': '_uninstall_hook',
}
