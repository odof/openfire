# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSaleManagementCommon(TestOFSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.payment_term_1 = cls.env["account.payment.term"].create(
            {
                "name": "Payment term 1",
            }
        )
        cls.custom_document_1 = cls.env["of.custom.document"].create(
            {
                "name": "Document 1",
            }
        )
        cls.sale_order_template_1 = cls.env["sale.order.template"].create(
            {
                "name": "Modèle de devis 1",
                "of_fiscal_position_id": cls.fiscal_pos_5_5.id,
                "of_payment_term_id": cls.payment_term_1.id,
                "of_custom_document_ids": [Command.set(cls.custom_document_1.ids)],
            }
        )
