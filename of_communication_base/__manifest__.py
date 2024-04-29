# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Communication",
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': 'OpenFire',
    'summary': "Gestion de la communication entre base (message, alertes, etc.)",
    'depends': [
        'base',
        'mail',
        'of_base',
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',

        'views/res_config_settings_views.xml',
        'views/of_communication_external_views.xml',
        'views/of_communication_internal_sender_views.xml',
        'views/of_communication_internal_users_views.xml',
        'views/of_communication_menus.xml',

        'data/ir_config_parameter.xml',
        'data/ir_cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'of_communication_base/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
