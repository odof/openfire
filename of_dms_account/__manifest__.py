# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / DMS Account",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "DMS Account - Ajout des documents de facturation dans le DMS",
    "depends": ["of_dms", "account"],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": True,
    "post_init_hook": "post_init_hook",
}
