# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name' : "OpenFire / Modes de paiement",
    'version' : "1.1",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "Generic Modules/Sales & Purchases",
    'description': """
    - Extension des modes de paiement aux paiements client ou fournisseur
    - Ajout règlement factures par LCR et prélèvement SEPA par échange de données informatisées (EDI)""",
    'depends' : [
        'account',
        'of_account_payment_mode',
    ],
    'init_xml' : [
        # Migration 'of_init.xml',
    ],
    'data' : [
        'security/ir.model.access.csv',
        # Migration 'of_mode_paiement_view.xml',
        'of_mode_paiement_edi_view.xml',
        # Migration 'wizard/wizard_edi_view.xml',
    ],
    'installable': False,
}
