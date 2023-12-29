# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tools import float_compare

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSaleOrderMarginControl(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Product data
        cls.category_margin_45 = (
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

        cls.product_margin_control = cls.create_product(
            {
                'name': 'Product Margin Control',
                'categ_id': cls.category_margin_45.id,
                'standard_price': 40,
                'list_price': 150,
                'default_code': 'BA_PMC_123',
            }
        )

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
        order_values = self._prepare_sale_order_values(dict(product=self.product_margin_control, price_unit=50))
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
