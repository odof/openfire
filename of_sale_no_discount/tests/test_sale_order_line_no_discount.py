# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from odoo.addons.of_sale.tests.common import TestOFSaleCommon


class TestOFSaleNoDiscountCommon(TestOFSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_forbidden_discount = cls.create_product(
            {
                'name': 'Product Forbidden Discount',
                'default_code': 'BA_FD_123',
                'of_forbidden_discount': True,
            }
        )

    def test_01_salesman_order_line_price_unit_edit_without_price_unit_group_nok(self):
        """Test that a salesman can't edit the price unit of a sale order line with a non forbidden discount product if
        he doesn't have the group group_of_can_modify_sale_price_unit"""
        order = self.env['sale.order'].with_user(self.user_salesman).create(self._prepare_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                with self.assertRaises(AssertionError):
                    line_form.price_unit = 100

    def test_02_salesman_order_line_price_unit_edit_with_price_unit_group_ok(self):
        """Test that a salesman can edit the price unit of a sale order line with a non forbidden discount product if
        he have the group group_of_can_modify_sale_price_unit"""
        self.user_salesman.write(
            {'groups_id': [(4, self.env.ref('of_sale_no_discount.group_of_can_modify_sale_price_unit').id)]}
        )
        order = self.env['sale.order'].with_user(self.user_salesman).create(self._prepare_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit = 100

    def test_03_salesman_order_line_discount_edit_without_price_unit_group_nok(self):
        """Test that a salesman can't edit the discount of a sale order line with a non forbidden discount product
        if he doesn't have the group group_of_can_modify_sale_price_unit"""
        order = self.env['sale.order'].with_user(self.user_salesman).create(self._prepare_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                with self.assertRaises(AssertionError):
                    line_form.of_discount_formula = 20

    def test_04_salesman_order_line_discount_edit_with_price_unit_group_ok(self):
        """Test that a salesman can edit the discount of a sale order line with a non forbidden discount product
        if he have the group group_of_can_modify_sale_price_unit"""
        self.user_salesman.write(
            {'groups_id': [(4, self.env.ref('of_sale_no_discount.group_of_can_modify_sale_price_unit').id)]}
        )
        order = self.env['sale.order'].with_user(self.user_salesman).create(self._prepare_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.of_discount_formula = 20

    def test_05_salesman_order_line_price_unit_edit_without_price_unit_group_nok(self):
        """Test that a responsible can't edit the price unit of a sale order line with a non forbidden discount product
        if he doesn't have the group group_of_can_modify_sale_price_unit"""
        order = self.env['sale.order'].with_user(self.user_sale_responsible).create(self._prepare_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                with self.assertRaises(AssertionError):
                    line_form.price_unit = 100

    def test_06_salesman_order_line_price_unit_edit_with_price_unit_group_ok(self):
        """Test that a responsible can edit the price unit of a sale order line with a non forbidden discount product if
        he have the group group_of_can_modify_sale_price_unit"""
        self.user_sale_responsible.write(
            {'groups_id': [(4, self.env.ref('of_sale_no_discount.group_of_can_modify_sale_price_unit').id)]}
        )
        order = self.env['sale.order'].with_user(self.user_sale_responsible).create(self._prepare_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit = 100

    def test_07_salesman_order_line_discount_edit_without_price_unit_group_nok(self):
        """Test that a responsible can't edit the discount of a sale order line with a non forbidden discount product
        if he doesn't have the group group_of_can_modify_sale_price_unit"""
        order = self.env['sale.order'].with_user(self.user_sale_responsible).create(self._prepare_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                with self.assertRaises(AssertionError):
                    line_form.of_discount_formula = 20

    def test_08_salesman_order_line_discount_edit_with_price_unit_group_ok(self):
        """Test that a responsible can edit the discount of a sale order line with a non forbidden discount product if
        he have the group group_of_can_modify_sale_price_unit"""
        self.user_sale_responsible.write(
            {'groups_id': [(4, self.env.ref('of_sale_no_discount.group_of_can_modify_sale_price_unit').id)]}
        )
        order = self.env['sale.order'].with_user(self.user_sale_responsible).create(self._prepare_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.of_discount_formula = 20

    def test_09_manager_order_line_price_unit_edit_ok(self):
        """Test that a manager can edit the price unit of a sale order line with a non forbidden discount product"""
        order = self.env['sale.order'].with_user(self.user_sale_manager).create(self._prepare_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit = 100

    def test_10_manager_order_line_discount_edit_ok(self):
        """Test that a manager can edit the discount of a sale order line with a non forbidden discount product"""
        order = self.env['sale.order'].with_user(self.user_sale_manager).create(self._prepare_sale_order_values())
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.of_discount_formula = 20

    def test_11_salesman_forbidden_product_order_line_price_unit_edit_nok(self):
        """Test that a salesman can't edit the price unit of a sale order line with a forbidden discount product"""
        order = (
            self.env['sale.order']
            .with_user(self.user_salesman)
            .create(self._prepare_sale_order_values(product=self.product_forbidden_discount))
        )
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                with self.assertRaises(AssertionError):
                    line_form.price_unit = 100

    def test_12_salesman_forbidden_product_order_line_discount_edit_ok(self):
        """Test that a salesman can't edit the discount of a sale order line with a forbidden discount product"""
        order = (
            self.env['sale.order']
            .with_user(self.user_salesman)
            .create(self._prepare_sale_order_values(product=self.product_forbidden_discount))
        )
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                with self.assertRaises(AssertionError):
                    line_form.of_discount_formula = 20

    def test_13_responsible_forbidden_product_order_line_price_unit_edit_without_group_nok(self):
        """Test that a responsible can't edit the price unit of a sale order line with a forbidden discount product if
        he doesn't have the group group_of_can_modify_sale_price_unit"""
        order = (
            self.env['sale.order']
            .with_user(self.user_sale_responsible)
            .create(self._prepare_sale_order_values(product=self.product_forbidden_discount))
        )
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                with self.assertRaises(AssertionError):
                    line_form.price_unit = 100

    def test_14_responsible_forbidden_product_order_line_price_unit_edit_with_group_ok(self):
        """Test that a responsible can edit the price unit of a sale order line with a forbidden discount product if
        he have the group group_of_can_modify_sale_price_unit"""
        self.user_sale_responsible.write(
            {'groups_id': [(4, self.env.ref('of_sale_no_discount.group_of_can_modify_sale_price_unit').id)]}
        )
        order = (
            self.env['sale.order']
            .with_user(self.user_sale_responsible)
            .create(self._prepare_sale_order_values(product=self.product_forbidden_discount))
        )
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit = 100

    def test_15_responsible_forbidden_product_order_line_discount_edit_without_group_nok(self):
        """Test that a responsible can't edit the discount of a sale order line with a forbidden discount product if
        he doesn't have the group group_of_can_modify_sale_price_unit"""
        order = (
            self.env['sale.order']
            .with_user(self.user_sale_responsible)
            .create(self._prepare_sale_order_values(product=self.product_forbidden_discount))
        )
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                with self.assertRaises(AssertionError):
                    line_form.of_discount_formula = 20

    def test_16_responsible_forbidden_product_order_line_discount_edit_with_group_ok(self):
        """Test that a responsible can edit the discount of a sale order line with a forbidden discount product if
        he have the group group_of_can_modify_sale_price_unit"""
        self.user_sale_responsible.write(
            {'groups_id': [(4, self.env.ref('of_sale_no_discount.group_of_can_modify_sale_price_unit').id)]}
        )
        order = (
            self.env['sale.order']
            .with_user(self.user_sale_responsible)
            .create(self._prepare_sale_order_values(product=self.product_forbidden_discount))
        )
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.of_discount_formula = 20

    def test_17_manager_forbidden_product_order_line_price_unit_edit_ok(self):
        """Test that a manager can edit the price unit of a sale order line with a non forbidden discount product"""
        order = (
            self.env['sale.order']
            .with_user(self.user_sale_manager)
            .create(self._prepare_sale_order_values(product=self.product_forbidden_discount))
        )
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit = 100

    def test_18_manager_forbidden_product_order_line_discount_edit_ok(self):
        """Test that a manager can edit the discount of a sale order line with a non forbidden discount product"""
        order = (
            self.env['sale.order']
            .with_user(self.user_sale_manager)
            .create(self._prepare_sale_order_values(product=self.product_forbidden_discount))
        )
        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.of_discount_formula = 20
