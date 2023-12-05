# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFSaleCommon(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # User data
        cls.user_salesman = cls.env['res.users'].create(
            {
                'name': 'user_salesman',
                'login': 'user_salesman',
                'email': 'user_salesman@openfire.fr',
                'groups_id': [(6, 0, [cls.env.ref('sales_team.group_sale_salesman').id])],
                'company_id': cls.company_fr.id,
            }
        )
        cls.user_sale_responsible = cls.env['res.users'].create(
            {
                'name': 'user_sale_responsible',
                'login': 'user_sale_responsible',
                'email': 'user_sale_responsible@openfire.fr',
                'groups_id': [(6, 0, [cls.env.ref('of_sale.of_group_sale_responsible').id])],
                'company_id': cls.company_fr.id,
            }
        )
        cls.user_sale_manager = cls.env['res.users'].create(
            {
                'name': 'user_sale_manager',
                'login': 'user_sale_manager',
                'email': 'user_sale_manager@openfire.fr',
                'groups_id': [(6, 0, [cls.env.ref('sales_team.group_sale_manager').id])],
                'company_id': cls.company_fr.id,
            }
        )

    def _prepare_empty_sale_order_values(self):
        return {
            'partner_id': self.customer_a.id,
            'partner_invoice_id': self.customer_a.id,
            'partner_shipping_id': self.customer_a.id,
            'pricelist_id': self.default_pricelist.id,
            'fiscal_position_id': self.fiscal_pos_5_5.id,
        }

    def _prepare_sale_order_values(self, salesman=False, product=False, price_unit=50, quantity=1):
        if not product:
            product = self.product_consu_a
        if not salesman:
            salesman = self.user_salesman
        return {
            'partner_id': self.customer_a.id,
            'partner_invoice_id': self.customer_a.id,
            'partner_shipping_id': self.customer_a.id,
            'pricelist_id': self.default_pricelist.id,
            'fiscal_position_id': self.fiscal_pos_5_5.id,
            'user_id': salesman.id,
            'order_line': [
                Command.create(
                    {
                        'product_id': product.id,
                        'product_uom_qty': quantity,
                        'tax_id': self.tax_base,
                        'price_unit': price_unit,
                    }
                ),
            ],
        }
