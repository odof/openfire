# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': u"OpenFire / Relance Factures",
    'version': "10.0.1.0.0",
    'author': "OpenFire",
    'license': "",
    'category': "OpenFire",
    'description': u"""
Relance Factures
----------------

Mise en place d'un workflow de relance pour les factures.
""",
    'website': "www.openfire.fr",
    'depends': [
        'of_account',
    ],
    'data': [
        'data/of_account_invoice_reminder_cron.xml',
        'data/of_account_invoice_reminder_data.xml',
        'views/of_account_invoice_reminder_views.xml',
        'views/res_partner_views.xml',
        'wizards/of_account_invoice_reminder_send_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
