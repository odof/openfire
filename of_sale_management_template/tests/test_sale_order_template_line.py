# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import Form

from odoo.addons.of_sale_management_template.tests.common import TestOFSaleManagementCommon


class TestOFSaleOrderTemplate(TestOFSaleManagementCommon):
    def test_01_sale_order_template_create(self):
        """Test creation of sale order template"""
        with Form(self.env['sale.order.template']) as template_form:
            template_form.name = "Sale order template create test"
            template_form.of_fiscal_position_id = self.fiscal_pos_10
            template_form.of_payment_term_id = self.payment_term_1
            template_form.of_custom_document_ids.add(self.custom_document_1)
            with template_form.sale_order_template_line_ids.new() as line_form:
                line_form.product_id = self.product_consu_a
                line_form.product_uom_qty = 1
            template = template_form.save()

        self.assertEqual(template.of_fiscal_position_id, self.fiscal_pos_10)
        self.assertEqual(template.of_payment_term_id, self.payment_term_1)
        self.assertEqual(template.of_custom_document_ids[0], self.custom_document_1)
        self.assertEqual(template.sale_order_template_line_ids[0].product_id, self.product_consu_a)
        self.assertEqual(template.sale_order_template_line_ids[0].product_uom_qty, 1)
        self.assertEqual(
            template.sale_order_template_line_ids[0].name,
            # get from product.template._recompute_product_name()
            '[BA_PCA_123] Brand A - Product Consu A\nBrand A Description\nProduct : Product Consu A',
        )

    def test_02_sale_order_create_with_template(self):
        """Test creation of sale order from template"""
        self.sale_order_template_1.write(
            {
                'sale_order_template_line_ids': [
                    Command.create({'product_id': self.product_consu_a.id, 'product_uom_qty': 3})
                ]
            }
        )

        sale_order = self.env['sale.order'].browse()
        # Création d'un devis à partir du modèle de devis
        order_values = self._prepare_sale_order_values()
        order_values['sale_order_template_id'] = self.sale_order_template_1.id
        sale_order = self.env['sale.order'].create(order_values)
        sale_order._onchange_sale_order_template_id()

        # Vérification des champs copiés
        self.assertEqual(sale_order.fiscal_position_id, self.fiscal_pos_5_5)
        self.assertEqual(sale_order.payment_term_id, self.payment_term_1)
        self.assertEqual(sale_order.of_custom_document_ids, self.custom_document_1)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.order_line[0].product_id, self.product_consu_a)
        self.assertEqual(sale_order.order_line[0].product_uom_qty, 3)
        self.assertEqual(
            sale_order.order_line[0].name,
            # get from product.template._recompute_product_name()
            '[BA_PCA_123] Brand A - Product Consu A\nBrand A Description\nProduct : Product Consu A',
        )
