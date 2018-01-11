# -*- encoding: utf-8 -*-

{
    "name" : "OpenFire / Implémentation obligations légales en France",
    "version" : "1.0",
    "author" : "OpenFire",
    "website" : "openfire.fr",
    "category" : "OpenFire",
    "description": """Module qui implémente les obligations légales en France :

- Certification logiciel de caisse
 """,
    "depends" : ['of_account_payment_mode'],
    "init_xml" : [ ],
    "demo_xml" : [ ],
    'css' : [
        "static/src/css/of_planning.css",
    ],
    "update_xml" : [
        'report/of_l10n_fr_certification_report_view.xml',
        'views/of_l10n_fr_certification_report_wizard_view.xml',
        "views/of_l10n_fr_certification.xml",
        'security/ir.model.access.csv',
        ],
    "installable": True,
}
