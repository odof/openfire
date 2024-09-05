# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Vue carte",
    'version': '16.0.1.0.1',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Ajout d'un type de vue carte (OpenStreetMap)",
    'depends': [
        'web',
        'of_geolocalize',
        'of_base',
    ],
    'data': [],
    'assets': {
        'web.assets_backend': [
            '/of_map_view/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
