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
        "security/ir.model.access.csv",
        "views/res_configs_settings_views.xml",
        "views/of_yousign_request_views.xml",
        "views/of_yousign_request_signatory_views.xml",
        "views/of_yousign_request_template_views.xml",
        "views/of_yousign_request_template_signatory_views.xml",
        "views/sale_order_views.xml",
        "views/menuitems.xml",
        "wizards/of_yousign_setup_wizard_views.xml",
        "wizards/of_yousign_direct_signature_wizard_views.xml",
        "reports/report_ir_attachment.xml",
        "reports/report_sale_order.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [],
        "web.assets_backend": [
            "of_yousign_connector/static/src/css/signature_style.css",
        ],
        "web.assets_frontend": [],
        "web.assets_tests": [],
        "web.qunit_suite_tests": [],
    },
    "external_dependencies": {"python": ["requests", "PyPDF2"]},
    "installable": True,
    "application": False,
    "auto_install": True,
}
