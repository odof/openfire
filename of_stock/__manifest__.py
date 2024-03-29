# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': u"OpenFire / Stock",
    'version': '10.0.1.2.0',
    'license': 'AGPL-3',
    'author': u"OpenFire",
    'category': u"OpenFire",
    'website': u"www.openfire.fr",
    'description': u"""
Extension OpenFire du module stock
==================================

- Possibilité de sélectionner le même article plusieurs fois dans le même inventaire. Les quantités seront cumulées.
- Ajout de l'id (non modifiable) et d'un champ note dans les lignes d'inventaire.
- Édition des lignes d'inventaire par le haut.
""",
    "depends": [
        "stock",
        "stock_account",
        "of_external",
        "of_product_brand",
    ],
    "data": [
        'security/of_stock_security.xml',
        'views/of_stock_views.xml',
        'views/stock_quant_views.xml',
        'views/purchase_order_views.xml',
        'wizards/of_picking_mass_validation_wizard_views.xml',
        'wizards/of_stock_date_confirmation_views.xml',
        'wizards/stock_backorder_confirmation_views.xml',
        'wizards/stock_immediate_transfer_views.xml',
        'wizards/of_specific_delivery_report_wizard_views.xml',
        'wizards/of_stock_inventory_reset_qty_wizard_views.xml',
        'wizards/of_stock_inventory_create_missing_wizard_views.xml',
        'reports/of_specific_delivery_report.xml',
        'reports/of_valued_delivery_report.xml',
        'reports/purchase_order_report.xml',
        'data/mail_template_data.xml',
        'hooks/post_hook.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
