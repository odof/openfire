# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Connecteur Poujoulat",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "category": "OpenFire",
    "summary": "Connecteur à la plateforme d'achats Poujoulat",
    "website": "https://www.openfire.fr",
    "depends": [
        "of_connector_base",
        "purchase",  # TODO : Switch to `of_purchase` when module is migrated
        "of_product_brand",
        "of_utils",
    ],
    "data": [
        "data/of_sanitize_query.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/purchase_order_views.xml",
        "views/product_template.xml",
        "wizards/of_wizard_poujoulat_cart_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
}
