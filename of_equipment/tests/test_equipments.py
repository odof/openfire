# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date, timedelta

from odoo import fields

from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestOFEquipment(TestOFPlanningCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.site_address_a1 = cls.env['res.partner'].create({'name': "Site Address A1", 'parent_id': cls.customer_a.id})
        cls.site_address_a2 = cls.env['res.partner'].create({'name': "Site Address A2", 'parent_id': cls.customer_a.id})
        cls.another_customer = cls.env['res.partner'].create({'name': "Another Customer"})
        cls.another_site_address = cls.env['res.partner'].create(
            {'name': "Another Site Address", 'parent_id': cls.another_customer.id}
        )

    def setUp(self):
        super().setUp()

    def test_01_name_search_with_partner_id_serial_number_ctx(self):
        """Test case for name search with partner ID and serial number in context.
        That should display the serial number with the partner name and should prefix the name with '-> ->' if partner
        in context is same as the equipment's partner.
        """
        equipment1 = self.env['of.equipment'].create(
            {'name': "CA/WS00001", 'product_id': self.product_wood_stove.id, 'customer_id': self.customer_a.id}
        )
        equipment2 = self.env['of.equipment'].create(
            {'name': "AC/WS00002", 'product_id': self.product_wood_stove.id, 'customer_id': self.another_customer.id}
        )
        equipment3 = self.env['of.equipment'].create(
            {'name': "CA/WS00003", 'customer_id': self.customer_a.id, 'product_id': self.product_wood_stove.id}
        )
        result = self.env['of.equipment'].with_context(partner_id_serial_number=self.customer_a.id).name_search()
        self.assertEqual(
            result,
            [
                (equipment1.id, '-> -> CA/WS00001 - Partner A'),
                (equipment3.id, '-> -> CA/WS00003 - Partner A'),
                (equipment2.id, 'AC/WS00002 - Another Customer'),
            ],
        )

    def test_02_name_search_with_address_prio_id_ctx(self):
        """Test case for name search with address priority ID in context.
        That should display equipment with the address of the context first, then equipment with the same partner
        and then the rest.
        """
        equipment1 = self.env['of.equipment'].create(
            {'name': "AC/WS00001", 'product_id': self.product_wood_stove.id, 'customer_id': self.another_customer.id}
        )
        equipment2 = self.env['of.equipment'].create(
            {'name': "CAA1/WS00002", 'product_id': self.product_wood_stove.id, 'customer_id': self.site_address_a1.id}
        )
        equipment3 = self.env['of.equipment'].create(
            {
                'name': "CAA1/WS00003",
                'product_id': self.product_wood_stove.id,
                'customer_id': self.customer_a.id,
                'site_address_id': self.site_address_a1.id,
            }
        )
        result = self.env['of.equipment'].with_context(address_prio_id=self.site_address_a1.id).name_search()
        self.assertEqual(
            result,
            [
                (equipment2.id, 'CAA1/WS00002 Poêle à bois - Partner A, Site Address A1'),
                (equipment3.id, 'CAA1/WS00003 Poêle à bois - Partner A'),
                (equipment1.id, 'AC/WS00001 Poêle à bois - Another Customer'),
            ],
        )

    def test_03_name_search_without_context(self):
        """Test case for name search without context.
        That should display the serial number with the partner name (by default sorted by id)
        """
        equipment1 = self.env['of.equipment'].create(
            {'name': "CA/WS00001", 'product_id': self.product_wood_stove.id, 'customer_id': self.customer_a.id}
        )
        equipment2 = self.env['of.equipment'].create(
            {'name': "AC/WS00002", 'product_id': self.product_wood_stove.id, 'customer_id': self.another_customer.id}
        )
        equipment3 = self.env['of.equipment'].create(
            {'name': "CA/WS00003", 'product_id': self.product_wood_stove.id, 'customer_id': self.customer_a.id}
        )
        result = self.env['of.equipment'].name_search()
        self.assertEqual(
            result,
            [
                (equipment1.id, 'CA/WS00001 Poêle à bois - Partner A'),
                (equipment2.id, 'AC/WS00002 Poêle à bois - Another Customer'),
                (equipment3.id, 'CA/WS00003 Poêle à bois - Partner A'),
            ],
        )

    def test_04_reseller_and_installer_partner(self):
        """Test case for reseller and installer partner.
        That should display the reseller and installer partner in the equipment form view.
        """
        # Create a reseller and an installer
        reseller = self.env['res.partner'].create({'name': 'Reseller'})
        installer = self.env['res.partner'].create({'name': 'Installer'})

        # Create a few equipment records with different reseller and installer
        equipment_values = [
            {
                'name': 'CA/WS00001',
                'customer_id': self.customer_a.id,
                'reseller_id': reseller.id,
                'installer_id': installer.id,
                'product_id': self.product_wood_stove.id,
            },
            {
                'name': 'CA/WS00002',
                'customer_id': self.customer_a.id,
                'reseller_id': reseller.id,
                'product_id': self.product_wood_stove.id,
            },
            {
                'name': 'CA/WS00003',
                'customer_id': self.customer_a.id,
                'installer_id': installer.id,
                'product_id': self.product_wood_stove.id,
            },
            {
                'name': 'CA/WS00004',
                'customer_id': self.customer_a.id,
                'product_id': self.product_wood_stove.id,
            },
        ]

        equipments = self.env['of.equipment'].create(equipment_values)

        # Check that the reseller and installer flags are set correctly
        self.assertTrue(all(e.reseller_id.of_is_reseller for e in equipments if e.reseller_id))
        self.assertTrue(all(e.installer_id.of_is_installer for e in equipments if e.installer_id))
        self.assertFalse(any(e.reseller_id.of_is_reseller for e in equipments if not e.reseller_id))
        self.assertFalse(any(e.installer_id.of_is_installer for e in equipments if not e.installer_id))

    def test_05_cron_recompute_warranty_type_daily(self):
        """Test case for cron_recompute_warranty_type_daily.
        That should recompute the warranty type of the equipment based on the end warranty date.
        """
        future_date = fields.Date.today() + timedelta(days=30)
        equipment_future = self.env['of.equipment'].create(
            {
                'name': 'CA/WS00001',
                'product_id': self.product_wood_stove.id,
                'customer_id': self.customer_a.id,
                'end_warranty_date': future_date,
            }
        )

        past_date = date.today() - timedelta(days=30)
        equipment_past = self.env['of.equipment'].create(
            {
                'name': 'CA/WS00001',
                'product_id': self.product_wood_stove.id,
                'customer_id': self.customer_a.id,
                'end_warranty_date': past_date,
            }
        )
        self.env['of.equipment'].cron_recompute_warranty_type_daily()
        self.assertEqual(equipment_future.warranty_type, 'in_warranty')
        self.assertEqual(equipment_past.warranty_type, 'expired')
