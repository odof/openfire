# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Sections avancées",
    'version': '16.0.1.0.0',
    'author': "OpenFire",
    'license': 'AGPL-3',
    'category': 'OpenFire',
    'summary': "Ajout des sections avancées sur les commandes",
    'website': "https://www.openfire.fr",
    'depends': [
        'of_account',
        'of_sale',
        'stock'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/account_move_views.xml',
        'reports/report_sale_order.xml',
        'reports/report_account_move.xml',
        'reports/report_sale_summary.xml',
        'wizards/of_sale_summary_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'of_sale_layout_category/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
