# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "OpenFire / Utilitaires",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'category': 'OpenFire',
    'sequence': 15,
    'summary': "Tools module for OpenFire",
    'website': 'https://www.openfire.fr',
    'description': "",
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
            # 'of_utils/static/src/scss/of_utils.scss',
            # 'of_utils/static/src/css/of_utils.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
