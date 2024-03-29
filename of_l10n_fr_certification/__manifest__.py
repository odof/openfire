# -*- coding: utf-8 -*-

{
    "name": u"OpenFire / Implémentation obligations légales en France",
    "version": "10.0.1.0.0",
    "author": "OpenFire",
    "website": "openfire.fr",
    "category": "OpenFire",
    "description": u"""Module qui implémente les obligations légales en France.

Certification logiciel de caisse :

- Créer une extourne comptable lors de la modification/annulation des paiements
- Téléchargement du certificat de conformité
- Message de confirmation lors d'une validation de facture
- Empêche la désinstallation des modules Odoo et Openfire de certification comptable
""",
    "depends": [
        'account_reversal'
    ],
    "update_xml": [
        'report/of_l10n_fr_certification_report_view.xml',
        'views/of_l10n_fr_certification_report_wizard_view.xml',
        "views/of_l10n_fr_certification.xml",
        'wizard/of_l10n_fr_certification_modification_paiement_wizard_view.xml',
        'security/ir.model.access.csv',
    ],
    "installable": True,
}
