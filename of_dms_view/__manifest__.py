# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / DMS View",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "DMS View - Ajout des documents de vente dans le DMS",
    "depends": ["of_dms"],
    "data": [
        "views/dms_directory.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/of_dms_view/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": True,
}
