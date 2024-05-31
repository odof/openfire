# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / CRM & Rapport de vente",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Sale report customization",
    'depends': [
        'of_sale_crm',
    ],
    'data': [
        'data/ir_config_parameter.xml',
        'security/res_groups.xml',
        # NOTE: Disabled for now as it is not used. Waiting for full SQL view migration.
        # 'views/res_config_settings_views.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
