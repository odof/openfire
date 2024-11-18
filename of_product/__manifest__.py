# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Produits (articles)",
    "version": "16.0.1.2.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "Module de gestion des produits (articles)",
    "depends": [
        "product",
        "of_utils",
    ],
    "data": [
        "data/ir_config_parameter.xml",
        "security/ir_rule.xml",
        "security/res_groups.xml",
        "views/product_views.xml",
        "views/product_supplierinfo_view.xml",
        "views/of_product_tag_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_category_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
