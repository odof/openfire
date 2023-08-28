# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.fields import Command
from odoo.tools import float_compare

from odoo.addons.of_account.tests.common import TestOFAccountCommon


class TestOFSaleOrderMarginControl(TestOFAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def create_company(cls, values):
        return cls.env["res.company"].create(values)

    @classmethod
    def create_product(cls, values):
        values.update({'type': 'consu', 'invoice_policy': 'order'})
        product_template = cls.env["product.template"].create(values)
        return product_template.product_variant_id

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

        cls.user_sale_manager = cls.env['res.users'].create(
            {
                'name': 'user_sale_manager',
                'login': 'user_sale_manager',
                'email': 'user_sale_manager@openfire.fr',
                'groups_id': [(6, 0, [cls.env.ref('sales_team.group_sale_manager').id])],
                'company_id': cls.company_fr.id,
            }
        )

        # Product and sale data
        cls.category = (
            cls.env['product.category']
            .with_company(cls.company_fr)
            .create(
                {
                    'name': 'Test margin < 45 %',
                    'of_main_product': True,
                    'of_margin_rate': 45.0,
                }
            )
        )

        cls.default_pricelist = (
            cls.env['product.pricelist']
            .with_company(cls.company_fr)
            .create(
                {
                    'name': 'default_pricelist',
                    'currency_id': cls.company_fr.currency_id.id,
                }
            )
        )

        cls.product_brand = (
            cls.env['of.product.brand']
            .with_company(cls.company_fr)
            .create(
                {
                    'name': 'Test brand',
                    'code': 'TB',
                    'partner_id': cls.supplier_a.id,
                }
            )
        )

        cls.of_product_1 = cls.create_product(
            {
                'name': 'of_product_test_margin_1',
                'categ_id': cls.category.id,
                'standard_price': 40,
                'list_price': 150,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': cls.env.ref('uom.product_uom_unit').id,
                'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
                'brand_id': cls.product_brand.id,
                'default_code': 'TB_TEST_1',
                'invoice_policy': 'order',
                'expense_policy': 'cost',
                'taxes_id': [Command.set([cls.tax_base.id])],
                'supplier_taxes_id': [(6, 0, [])],
            }
        )

    def _prepare_sale_order_values(self):
        return {
            'partner_id': self.customer_a.id,
            'partner_invoice_id': self.customer_a.id,
            'partner_shipping_id': self.customer_a.id,
            'pricelist_id': self.default_pricelist.id,
            'fiscal_position_id': self.fiscal_pos_5_5.id,
            'order_line': [
                Command.create(
                    {
                        'product_id': self.of_product_1.id,
                        'product_uom_qty': 1,
                        'tax_id': self.tax_base,
                        'price_unit': 50,
                    }
                ),
            ],
        }

    def _create_and_confirm_sale_order_as_user(self, margin_control=False, as_user=None):
        """Create a sale order and confirm it as a given user.
        The margin control can be activated or not.
        The price of the sale order line is set to 50 € to have a margin of 20 %.

        :param margin_control: True to activate the margin control, False otherwise.
        :param as_user: The user who will confirm the sale order.
        :return: The result of the action.
        """
        if as_user is None:
            as_user = self.user_salesman

        config = self.env['res.config.settings'].create({'of_sale_order_margin_control': margin_control})
        config.execute()
        order_values = self._prepare_sale_order_values()
        sale_order = self.env['sale.order'].with_user(as_user).create(order_values)
        self.assertEqual(
            float_compare(sale_order.of_margin_percent, 20.0, precision_digits=2),
            0,
        )
        return sale_order.action_verification_confirm()

    def test_01_margin_control_order_confirm_salesman(self):
        """Test margin control on sale order confirmation as a salesman.
        The salesman should be able to confirm the sale order because the margin control is not activated.
        """
        res = self._create_and_confirm_sale_order_as_user(
            margin_control=False,
            as_user=self.user_salesman,
        )
        self.assertEqual(res, True)

    def test_02_margin_control_order_confirm_salesman(self):
        """Test margin control on sale order confirmation as a salesman.
        The salesman shouldn't be able to confirm the sale order because the margin (20 %) is under the required
        margin (45 %).
        """

        action = self._create_and_confirm_sale_order_as_user(
            margin_control=True,
            as_user=self.user_salesman,
        )
        # A wizard should be opened to warn the user about the margin.
        self.assertEqual(action['res_model'], 'of.sale.order.verification')
        self.assertEqual(action['context']['default_type'], 'margin')

    def test_03_margin_control_order_confirm_manager(self):
        """Test margin control on sale order confirmation as a salesman.
        The manager should be able to confirm the sale order because the margin control is not applied to him.
        """
        res = self._create_and_confirm_sale_order_as_user(
            margin_control=True,
            as_user=self.user_sale_manager,
        )
        self.assertEqual(res, True)

    def test_04_margin_control_order_confirm_admin(self):
        """Test margin control on sale order confirmation as a salesman.
        The admin should be able to confirm the sale order because the margin control is not applied to him.
        """
        res = self._create_and_confirm_sale_order_as_user(
            margin_control=True,
            as_user=self.env.user,
        )
        self.assertEqual(res, True)
