# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Gestion CRM des fabricants",
    "version": "16.0.1.2.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "CRM management of manufacturers",
    "depends": [
        "of_base",
        "of_product_brand",
    ],
    "data": [
        "views/res_partner_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
