# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Communication Customer",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': 'OpenFire',
    'summary': "Gestion de la communication",
    'depends': [
        'base',
        'mail',
        'of_communication_base',
    ],
    'data': [
        'views/of_communication_customer_views.xml',

        'data/ir_cron.xml',
    ],
    "assets": {
        'web.assets_backend': [
            'of_communication_customer/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
