# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "OpenFire / Achats",
    'version': "16.0.1.0.0",
    'license': 'AGPL-3',
    'author': "OpenFire",
    'category': "Purchases",
    'summary': "Modifications OpenFire pour les commandes fournisseur",
    'website': "www.openfire.fr",
    'depends': [
        'purchase',
        'purchase_stock', #J'ai ajouté cette dependance car picking_ids est définit dans purchase_stock
        'of_product',
        # 'of_external',
        'of_sale_stock_purchase', #> get_cost
        'sale_stock',
    ],
    'data': [
        'security/of_purchase_security.xml',
        # 'report/purchase_report_templates.xml',
        # 'report/purchase_reports.xml',
        'views/stock_picking_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_order_line_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,

}
