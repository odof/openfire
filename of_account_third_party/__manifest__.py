
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'OpenFire / Comptes de tiers',
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'OpenFire',
    'category': 'Accounting',
    'depends': [
        'of_account',
        'of_utils',
        'partner_manual_rank'
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
