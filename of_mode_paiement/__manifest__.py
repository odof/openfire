# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenFire
#
##############################################################################

{
    'name' : "OpenFire / Modes de paiement",
    'version' : "10.0.1.0.0",
    'author' : "OpenFire",
    'website' : "www.openfire.fr",
    'category' : "Generic Modules/Sales & Purchases",
    'description': """
    - Ajout compte bancaire dans les modes de paiement
    - Règlement factures par LCR et prélèvement SEPA par échange de données informatisées (EDI)
    """,
    'depends' : [
        'account',
        'of_account_payment_mode',
    ],
    'init_xml' : [
    ],
    'data' : [
        'security/ir.model.access.csv',
        'views/of_mode_paiement_edi_view.xml',
    ],
    'installable': True,
}
