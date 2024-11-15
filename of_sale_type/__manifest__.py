# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Types de devis",
    "version": "16.0.1.2.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "Extension du module OCA sale_order_type",
    "depends": [
        "sale_order_type",  # OCA/sale-workflow
        "of_sale_management_template",
    ],
    "data": [
        "views/sale_order_type.xml",
        "views/res_partner.xml",
        "views/sale_order_views.xml",
        "views/sale_order_line_views.xml",
        "views/sale_order_template.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
