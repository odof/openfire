# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.of_dms.tests.common import TestOFDMSCommon

from ..hooks import post_init_hook


class TestOFDMSStockCommon(TestOFDMSCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        post_init_hook(cls.cr, cls.env)

        cls.location = cls.env["stock.location"].create({"name": "Test location", "usage": "internal"})
        cls.location_customers = cls.env["stock.location"].create(
            {"name": "Test location customers", "usage": "customer"}
        )
        cls.outgoing_sequence = cls.env["ir.sequence"].create(
            {
                "name": "outgoing seq",
                "implementation": "standard",
                "padding": 1,
                "number_increment": 1,
            }
        )
        cls.incoming_sequence = cls.env["ir.sequence"].create(
            {
                "name": "incoming seq",
                "implementation": "standard",
                "padding": 1,
                "number_increment": 1,
            }
        )
        cls.outgoing_picking_type = cls.env["stock.picking.type"].create(
            {
                "name": "Test picking type",
                "code": "outgoing",
                "sequence_id": cls.outgoing_sequence.id,
                "sequence_code": "OUT",
            }
        )

        cls.incoming_picking_type = cls.env["stock.picking.type"].create(
            {
                "name": "Test picking type",
                "code": "incoming",
                "sequence_id": cls.incoming_sequence.id,
                "sequence_code": "IN",
            }
        )

        cls.stock_directories = (
            cls.directory_model.with_context({"active_test": False})
            .search(
                [
                    ("res_model", "=", "stock.picking"),
                    (
                        "parent_id",
                        "in",
                        [
                            cls.customer_a.of_dms_directory_id.id,
                            cls.supplier_a.of_dms_directory_id.id,
                            cls.supplier_b.of_dms_directory_id.id,
                        ],
                    ),
                ]
            )
            .sorted("id")
        )
