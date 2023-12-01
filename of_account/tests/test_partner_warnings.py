# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import Form

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFResPartnerWarnings(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_with_warning = cls.env['res.partner'].create(
            {
                'name': 'Test partner with warning',
                'of_is_account_warn': True,
                'invoice_warn_msg': 'Test warning',
            }
        )
        cls.partner_with_blocking_warning = cls.env['res.partner'].create(
            {
                'name': 'Test partner with blocking warning',
                'of_is_account_warn': True,
                'invoice_warn_msg': 'Test warning',
                'of_warn_block': True,
            }
        )
        cls.user_salesman = cls.env['res.users'].create(
            {
                'name': 'user_salesman',
                'login': 'user_salesman',
                'email': 'user_salesman@openfire.fr',
                'groups_id': [Command.set([cls.env.ref('sales_team.group_sale_salesman').id])],
                'company_id': cls.company_fr.id,
            }
        )

    def test_01_res_partner_invoice_warning_readonly(self):
        """Test readonly mode of invoice_warning field on res.partner for a non accounting user"""
        with Form(self.env['res.partner'].with_user(self.user_salesman)) as partner_form:
            partner_form.name = 'Test partner 1'
            with self.assertRaises(AssertionError):
                partner_form.of_is_account_warn = True

        with Form(self.env['res.partner'].with_user(self.user_accountant)) as partner_form:
            partner_form.name = 'Test partner 2'
            partner_form.of_is_account_warn = True
            partner_form.invoice_warn_msg = 'Test warning'  # required field when of_is_account_warn is True

    def test_02_res_partner_invoice_non_blocking_warning(self):
        move = (
            self.env['account.move']
            .with_user(self.user_accountant)
            .create({'partner_id': self.partner_with_warning.id})
        )
        res = move._onchange_partner_id_warning()
        self.assertDictEqual(
            res, {'warning': {'title': 'Avertissement pour Test partner with warning', 'message': 'Test warning'}}
        )
        self.assertEqual(move.partner_id, self.partner_with_warning)

    def test_03_res_partner_invoice_blocking_warning(self):
        move = (
            self.env['account.move']
            .with_user(self.user_accountant)
            .create({'partner_id': self.partner_with_blocking_warning.id})
        )
        res = move._onchange_partner_id_warning()
        self.assertDictEqual(
            res,
            {'warning': {'title': 'Avertissement pour Test partner with blocking warning', 'message': 'Test warning'}},
        )
        self.assertEqual(move.partner_id, self.env['res.partner'].browse())
