# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "OpenFire / Echéancier de paiement des Factures",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "OpenFire",
    "website": "https://www.openfire.fr",
    "category": "OpenFire",
    "summary": "Echéancier de paiement des Factures",
    "depends": [
        "of_invoice_report_setting",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/account_payment_term_views.xml",
        "views/of_invoice_document_layout_views.xml",
        "reports/ir_actions_report_templates.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
