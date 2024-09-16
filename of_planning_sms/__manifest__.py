# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / SMS Planning",
    'version': "16.0.1.0.0",
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': "OpenFire",
    'summary': "Module de SMS OpenFire pour le planning",
    'website': "https://www.openfire.fr",
    'depends': [
        'of_sms',
        'of_planning',
    ],
    'data': [
        'data/ir_cron.xml',
        'data/sms_template.xml',
        'data/ir_actions_server.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
}
