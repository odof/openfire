# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
from odoo.tests.common import at_install, post_install, TransactionCase


@at_install(False)
@post_install(True)
class OFTestAccountTransactionCase(TransactionCase):

    def setUp(self):
        """
        Making some basic configuration for accounting
        self.test_mode_payment : payment_mode that should be used in order to create payments
        """
        super(OFTestAccountTransactionCase, self).setUp()
        mode_payment_obj = self.env['of.account.payment.mode']
        user = self.env.user
        account_journal = self.env['account.journal'].search(
            [('type', 'in', ('bank', 'cash')),
             '|','|',('company_id','=',False),
                     ('company_id','child_of',[user.company_id.id]),
                ('company_id','parent_of',[user.company_id.id])])
        if account_journal:
            mode_payment_vals = {
                'name': u"Mode de paiement de test",
                'company_id': user.company_id.id,
                'journal_id': account_journal[0].id,
            }
            mode_payment = mode_payment_obj.create(mode_payment_vals)
            self.test_mode_payment = mode_payment
        else:
            self.test_mode_payment = False

