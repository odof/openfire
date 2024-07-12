# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / DMS",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "Personnalisation du DMS",
    "depends": [
        "dms",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/dms_access_group.xml",
        "data/dms_storage.xml",
        "data/dms_directory.xml",
        "views/dms_file_views.xml",
        "views/dms_directory_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}
