# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Taxes",
    'version': '16.0.1.0.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'website': "https://www.openfire.fr",
    'category': "OpenFire",
    'summary': "Personnalisation de la gestion des taxes",
    'description': "",
    'depends': [
        'of_account',
        'of_sale',
        'purchase'
    ],
    'data': [
        'views/account_fiscal_position_views.xml',
        'views/account_tax_views.xml',
        'views/sale_order_views.xml',
        'views/sale_order_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
