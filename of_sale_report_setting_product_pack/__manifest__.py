# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Configuration d'impression & Kits produits",
    'version': '16.0.1.1.0',
    'license': 'AGPL-3',
    'author': "OpenFire",
    'summary': "Module de lien entre la configuration d'impression et les kits produits",
    'category': 'OpenFire',
    'website': 'https://www.openfire.fr',
    'depends': [
        'of_sale_product_pack',
        'of_product_pack',
        'of_sale',
        'of_sale_report_setting',
    ],
    'data': [
        'views/sale_order_views.xml',
        'reports/report_sale_order.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
