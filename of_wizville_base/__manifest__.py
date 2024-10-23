# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "OpenFire / Wizville base",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "Module de base pour l'implémentation de l'API Wizville",
    "depends": [
        "of_connector_base",
        "of_sale",
    ],
    "data": [
        "data/ir_cron.xml",
        "data/of_sanitize_query.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/res_company_views.xml",
        "views/res_partner_views.xml",
        "views/product_template_views.xml",
        "views/of_wizville_history_views.xml",
        "views/menuitems.xml",
    ],
    "qweb": [],
    "external_dependencies": {
        "python": [
            "paramiko",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "pre_init_hook": "pre_init_hook",
}
