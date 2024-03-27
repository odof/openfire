# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Openfire / Commentaires de vente",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': 'OpenFire',
    'summary': "Module d'extension pour les commentaires de vente",
    'depends': [
        'sale_comment_template',
        'of_sale'
    ],
    'data': [
        'data/ir_config_parameter.xml',
        'views/base_comment_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
