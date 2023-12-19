# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Utilitaires",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'category': 'OpenFire',
    'summary': "Module de fonctions utilitaires pour OpenFire",
    'website': 'https://www.openfire.fr',
    'depends': [
        'of_base',
        'sale',
    ],
    'data': [
        'data/days_data.xml',
        'data/months_data.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'of_utils/static/src/scss/of_utils.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
