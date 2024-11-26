# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Rapports personnalisés",
    "version": "16.0.1.0.2",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "Documents",
    "summary": "Module de rapports personnalisés",
    "depends": ["of_base"],
    "external_dependencies": {
        "python": ["pdfminer", "pypdftk"],
    },
    "data": [
        "security/ir.model.access.csv",
        "report/ir_actions_report_templates.xml",
        "views/ir_actions_views.xml",
        "views/of_custom_document_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
