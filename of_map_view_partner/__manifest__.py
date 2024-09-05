# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Vue carte pour les partenaires",
    'version': '16.0.1.0.1',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Ajout de la vue carte (OpenStreetMap) pour les contacts",
    'depends': [
        'contacts',
        'of_map_view',
    ],
    'data': [
        'data/data.xml',
        'views/res_partner_views.xml',
        ],
    'assets': {
        'web.assets_backend': [
            '/of_map_view_partner/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': True,
    'uninstall_hook': '_uninstall_hook',
}
