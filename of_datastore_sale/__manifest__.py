# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "OpenFire / Connecteur ventes",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "category": "OpenFire",
    "summary": "Connecteur de ventes pour Product Datastore",
    "website": "https://www.openfire.fr",
    "depends": [
        "purchase_stock",
        "stock_dropshipping",
        "of_sale",
        "of_datastore_common_sp",
    ],
    "data": [
        "data/of_sanitize_query.xml",
        "security/of_datastore_sale_security.xml",
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/of_product_brand_views.xml",
        "views/of_datastore_sale_views.xml",
        "views/res_config_settings_views.xml",
        "views/menuitems.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
