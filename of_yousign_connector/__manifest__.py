# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Connecteur YouSign",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "category": "OpenFire",
    "summary": "Gestion des e-signatures YouSign",
    "website": "https://www.openfire.fr",
    "depends": [
        "of_sale",
        "of_connector_base",
    ],
    "data": [
        "views/res_configs_settings_views.xml",
        "views/of_yousign_request_views.xml",
    ],
    "assets": {},
    "external_dependencies": {"python": ["requests"]},
    "installable": True,
    "application": False,
    "auto_install": True,
}
