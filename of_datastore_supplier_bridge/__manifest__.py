# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


{
    "name": "OpenFire / Base centrale intermédiaire des articles",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "Base centrale intermédiaire des articles",
    "depends": ["of_datastore_product", "of_datastore_supplier"],
    "data": [
        "views/of_datastore_supplier_bridge_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": True,
}
