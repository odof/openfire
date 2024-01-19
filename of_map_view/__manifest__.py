# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Vue carte",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Ajout d'un type de vue carte (OpenStreetMap) dans les contacts",
    'depends': [
        'contacts',
        'web',
        'of_geolocalize',
    ],
    'data': ['views/of_partner_views.xml'],
    'assets': {
        'web.assets_backend': [
            '/of_map_view/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'uninstall_hook': '_uninstall_hook',
}
