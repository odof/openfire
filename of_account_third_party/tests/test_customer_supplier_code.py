# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestResPartnerCustomerSupplierCode(TestOFAccountCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_obj = cls.env['res.partner']
        cls.company_obj = cls.env['res.company']
        cls.ir_property_obj = cls.env['ir.property']

        cls.default_account_receivable = cls.ir_property_obj._get('property_account_receivable_id', 'res.partner')
        cls.default_account_payable = cls.ir_property_obj._get('property_account_payable_id', 'res.partner')
        cls.company_fr.of_customer_code = "('411%05i' % partner.id, partner.name)"
        cls.company_fr.of_supplier_code = "('401%05i' % partner.id, partner.name)"
        cls.partner_baptiste = cls.partner_obj.create({'name': 'Baptiste'})

    def test_01_account_move_customer(self):
        """
        Test that the receivable account is correctly set on the partner when creating a customer invoice.
        """
        self.assertEqual(self.partner_baptiste.property_account_receivable_id, self.default_account_receivable)
        with Form(
            self.env['account.move'].with_context(
                default_move_type='out_invoice', default_company_id=self.company_fr.id
            )
        ) as move:
            move.partner_id = self.partner_baptiste

            self.assertNotEqual(self.partner_baptiste.property_account_receivable_id, self.default_account_receivable)
            self.assertEqual(
                self.partner_baptiste.property_account_receivable_id.display_name,
                f'411{self.partner_baptiste.id:05d} {self.partner_baptiste.name}',  # noqa
            )

    def test_02_account_move_supplier(self):
        """Test that the payable account is correctly set on the partner when creating a supplier"""
        self.assertEqual(self.partner_baptiste.property_account_payable_id, self.default_account_payable)
        with Form(
            self.env['account.move'].with_context(default_move_type='in_invoice', default_company_id=self.company_fr.id)
        ) as move:
            move.partner_id = self.partner_baptiste

            self.assertNotEqual(self.partner_baptiste.property_account_payable_id, self.default_account_payable)
            self.assertEqual(
                self.partner_baptiste.property_account_payable_id.display_name,
                f'401{self.partner_baptiste.id:05d} {self.partner_baptiste.name}',  # noqa
            )
