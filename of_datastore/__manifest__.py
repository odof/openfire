# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Datastore",
    'version': "16.0.1.0.0",
    "license": 'AGPL-3',
    'author': "OpenFire",
    "website": "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Gestion des bases centralisées",
    'depends': ['of_datastore_connector', 'of_account', 'stock'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'of_datastore/static/src/js/list_renderer.js',
            'of_datastore/static/src/scss/list_renderer.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
