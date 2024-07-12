# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from .common import TestOFDMSStockCommon


class TestOFDMSServiceOFServiceRequest(TestOFDMSStockCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pickings = (
            cls.env["stock.picking"]
            .create(
                [
                    {
                        "name": "Picking 1",
                        "partner_id": cls.customer_a.id,
                        "picking_type_id": cls.outgoing_picking_type.id,
                        "location_id": cls.location.id,
                        "location_dest_id": cls.location_customers.id,
                    },
                    {
                        "name": "Picking 2",
                        "partner_id": cls.customer_a.id,
                        "picking_type_id": cls.outgoing_picking_type.id,
                        "location_id": cls.location.id,
                        "location_dest_id": cls.location_customers.id,
                    },
                    {
                        "name": "Picking 3",
                        "partner_id": cls.supplier_a.id,
                        "picking_type_id": cls.incoming_picking_type.id,
                        "location_id": cls.location.id,
                        "location_dest_id": cls.location_customers.id,
                    },
                    {
                        "name": "Picking 4",
                        "partner_id": cls.supplier_a.id,
                        "picking_type_id": cls.outgoing_picking_type.id,
                        "location_id": cls.location.id,
                        "location_dest_id": cls.location_customers.id,
                    },
                    {
                        "name": "Picking 5",
                        "partner_id": cls.supplier_b.id,
                        "picking_type_id": cls.incoming_picking_type.id,
                        "location_id": cls.location.id,
                        "location_dest_id": cls.location_customers.id,
                    },
                    {
                        "name": "Picking 6",
                        "partner_id": cls.supplier_b.id,
                        "picking_type_id": cls.incoming_picking_type.id,
                        "location_id": cls.location.id,
                        "location_dest_id": cls.location_customers.id,
                    },
                ]
            )
            .sorted("id")
        )

        cls.attachments = cls.create_attachments(
            [
                {
                    "name": "test.txt",
                    "res_model": "stock.picking",
                    "res_id": cls.pickings[0].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "stock.picking",
                    "res_id": cls.pickings[2].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "stock.picking",
                    "res_id": cls.pickings[4].id,
                    "datas": cls.content_base64(),
                },
            ]
        ).sorted("id")

        cls.real_files = cls.file_model.search(
            [("of_type", "=", "real"), ("attachment_id", "in", cls.attachments.ids)]
        ).sorted("id")
        cls.virtual_files = cls.file_model.search(
            [
                ("of_type", "=", "virtual"),
                ("of_virtual_res_model", "=", cls.env.ref("stock.model_stock_picking").id),
                ("of_virtual_res_id", "in", cls.pickings.ids),
            ]
        ).sorted("id")

    def test_01_create_attachment_stock(self):
        """Test that the attachment are correctly created"""
        self.assertRecordValues(
            self.attachments,
            [
                {
                    "name": "test.txt",
                    "res_model": "stock.picking",
                    "res_id": self.pickings[0].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "stock.picking",
                    "res_id": self.pickings[2].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "stock.picking",
                    "res_id": self.pickings[4].id,
                    "datas": self.content_base64(),
                },
            ],
        )

    def test_02_create_virtual_files_stock(self):
        """Test that the virtual files are correctly created"""
        self.assertRecordValues(
            self.virtual_files,
            [
                {
                    "of_type": "virtual",
                    "name": "Delivery Slip - Partner A - Picking 1.pdf",
                    "directory_id": self.stock_directories[1].id,
                    "attachment_id": False,
                    "res_model": "stock.picking",
                    "of_virtual_res_model": self.env.ref("stock.model_stock_picking").id,
                    "of_virtual_res_id": self.pickings[0].id,
                },
                {
                    "of_type": "virtual",
                    "name": "Delivery Slip - Partner A - Picking 2.pdf",
                    "directory_id": self.stock_directories[1].id,
                    "attachment_id": False,
                    "res_model": "stock.picking",
                    "of_virtual_res_model": self.env.ref("stock.model_stock_picking").id,
                    "of_virtual_res_id": self.pickings[1].id,
                },
                {
                    "of_type": "virtual",
                    "name": "Delivery Slip - Supplier A - Picking 4.pdf",
                    "directory_id": self.stock_directories[3].id,
                    "attachment_id": False,
                    "res_model": "stock.picking",
                    "of_virtual_res_model": self.env.ref("stock.model_stock_picking").id,
                    "of_virtual_res_id": self.pickings[3].id,
                },
                {
                    "of_type": "virtual",
                    "name": "Delivery Slip - Supplier A - Picking 3.pdf",
                    "directory_id": self.stock_directories[2].id,
                    "attachment_id": False,
                    "res_model": "stock.picking",
                    "of_virtual_res_model": self.env.ref("stock.model_stock_picking").id,
                    "of_virtual_res_id": self.pickings[2].id,
                },
                {
                    "of_type": "virtual",
                    "name": "Delivery Slip - Supplier B - Picking 5.pdf",
                    "directory_id": self.stock_directories[4].id,
                    "attachment_id": False,
                    "res_model": "stock.picking",
                    "of_virtual_res_model": self.env.ref("stock.model_stock_picking").id,
                    "of_virtual_res_id": self.pickings[4].id,
                },
                {
                    "of_type": "virtual",
                    "name": "Delivery Slip - Supplier B - Picking 6.pdf",
                    "directory_id": self.stock_directories[4].id,
                    "attachment_id": False,
                    "res_model": "stock.picking",
                    "of_virtual_res_model": self.env.ref("stock.model_stock_picking").id,
                    "of_virtual_res_id": self.pickings[5].id,
                },
            ],
        )

    def test_03_create_real_files_stock(self):
        """Test that the real files are correctly created"""
        self.assertRecordValues(
            self.real_files,
            [
                {
                    "of_type": "real",
                    "name": "test.txt",
                    "directory_id": self.stock_directories[1].id,
                    "attachment_id": self.attachments[0].id,
                    "res_model": "stock.picking",
                },
                {
                    "of_type": "real",
                    "name": "test-2.txt",
                    "directory_id": self.stock_directories[2].id,
                    "attachment_id": self.attachments[1].id,
                    "res_model": "stock.picking",
                },
                {
                    "of_type": "real",
                    "name": "test-3.txt",
                    "directory_id": self.stock_directories[4].id,
                    "attachment_id": self.attachments[2].id,
                    "res_model": "stock.picking",
                },
            ],
        )

    def test_04_update_directory_stock(self):
        """Test that the directories are correctly updated"""
        self.assertRecordValues(
            [
                self.customer_a.of_dms_directory_id,
                self.supplier_a.of_dms_directory_id,
                self.supplier_b.of_dms_directory_id,
            ],
            [
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.stock_directories[1].ids,
                },
                {
                    "active": True,
                    "count_directories": 2,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.stock_directories[2:4].ids,
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.stock_directories[4].ids,
                },
            ],
        )

    def test_05_update_subdirectory_stock(self):
        """Test that the subdirectories are correctly updated"""
        self.assertRecordValues(
            self.stock_directories,
            [
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Delivery Slips",
                    "res_model": "stock.picking",
                    "parent_id": self.customer_a.of_dms_directory_id.id,
                    "of_code": "incoming",
                },
                {
                    "active": True,
                    "count_files": 3,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[0].id,
                        self.virtual_files[1].id,
                        self.real_files[0].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Receipt Slips",
                    "res_model": "stock.picking",
                    "parent_id": self.customer_a.of_dms_directory_id.id,
                    "of_code": "outgoing",
                },
                {
                    "active": True,
                    "count_files": 2,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[3].id,
                        self.real_files[1].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Delivery Slips",
                    "res_model": "stock.picking",
                    "parent_id": self.supplier_a.of_dms_directory_id.id,
                    "of_code": "incoming",
                },
                {
                    "active": True,
                    "count_files": 1,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[2].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Receipt Slips",
                    "res_model": "stock.picking",
                    "parent_id": self.supplier_a.of_dms_directory_id.id,
                    "of_code": "outgoing",
                },
                {
                    "active": True,
                    "count_files": 3,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[4].id,
                        self.virtual_files[5].id,
                        self.real_files[2].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Delivery Slips",
                    "res_model": "stock.picking",
                    "parent_id": self.supplier_b.of_dms_directory_id.id,
                    "of_code": "incoming",
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Receipt Slips",
                    "res_model": "stock.picking",
                    "parent_id": self.supplier_b.of_dms_directory_id.id,
                    "of_code": "outgoing",
                },
            ],
        )
