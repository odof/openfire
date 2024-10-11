# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFPartnerWarning(TestOFSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_with_warning = cls.env["res.partner"].create(
            {
                "name": "Partner with warning",
                "of_is_lead_warn": True,
                "invoice_warn_msg": "This is a warning message",
            }
        )

    def test_01_no_partner_warning(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Test lead",
                "partner_id": self.customer_a.id,
            }
        )
        res = lead._onchange_partner_id_warning()
        self.assertEqual(res, None)

    def test_02_partner_warning(self):
        self._create_assert_crm_lead()

    def test_03_partner_blocking_warning(self):
        self.partner_with_warning.of_warn_block = True
        lead = self._create_assert_crm_lead()
        self.assertEqual(lead.partner_id, self.env["res.partner"].browse())

    def _create_assert_crm_lead(self):
        result = self.env["crm.lead"].create({"name": "Test lead", "partner_id": self.partner_with_warning.id})
        res = result._onchange_partner_id_warning()
        self.assertEqual(res["warning"]["message"], "This is a warning message")
        return result
