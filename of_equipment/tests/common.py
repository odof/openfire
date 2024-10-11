# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestOFEquipmentCommon(TestOFPlanningCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.equipment_wood_stove = cls.env["of.equipment"].create(
            {
                "name": "CA/WS00001",
                "product_id": cls.product_wood_stove.id,
                "customer_id": cls.customer_a.id,
                "site_address_id": cls.customer_a.id,
            }
        )
        cls.equipment_ash_vacuum_cleaner = cls.env["of.equipment"].create(
            {
                "name": "CA/AVC00001",
                "product_id": cls.product_ash_vacuum_cleaner.id,
                "customer_id": cls.customer_a.id,
                "site_address_id": cls.customer_a.id,
            }
        )
