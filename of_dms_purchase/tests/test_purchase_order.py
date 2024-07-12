# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from .common import TestOFDMSPurchaseCommon


class TestOFDMSPurchasePurchaseOrder(TestOFDMSPurchaseCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.purchases = (
            cls.env["purchase.order"]
            .create(
                [
                    {
                        "partner_id": cls.customer_a.id,
                    },
                    {
                        "partner_id": cls.supplier_a.id,
                    },
                    {
                        "partner_id": cls.supplier_b.id,
                    },
                ]
            )
            .sorted("id")
        )

        cls.attachments = cls.create_attachments(
            [
                {
                    "name": "test.txt",
                    "res_model": "purchase.order",
                    "res_id": cls.purchases[0].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "purchase.order",
                    "res_id": cls.purchases[1].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "purchase.order",
                    "res_id": cls.purchases[2].id,
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
                ("of_virtual_res_model", "=", cls.env.ref("purchase.model_purchase_order").id),
                ("of_virtual_res_id", "in", cls.purchases.ids),
            ]
        ).sorted("id")

    def test_01_create_attachment_purchase(self):
        """Test that the attachment are correctly created"""
        self.assertRecordValues(
            self.attachments,
            [
                {
                    "name": "test.txt",
                    "res_model": "purchase.order",
                    "res_id": self.purchases[0].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "purchase.order",
                    "res_id": self.purchases[1].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "purchase.order",
                    "res_id": self.purchases[2].id,
                    "datas": self.content_base64(),
                },
            ],
        )

    def test_02_create_virtual_files_purchase(self):
        """Test that the virtual files are correctly created"""
        self.assertRecordValues(
            self.virtual_files,
            [
                {
                    "of_type": "virtual",
                    "name": f"Request for Quotation - {self.purchases[0].name}.pdf",
                    "directory_id": self.purchase_directories[0].id,
                    "attachment_id": False,
                    "res_model": "purchase.order",
                    "of_virtual_res_model": self.env.ref("purchase.model_purchase_order").id,
                    "of_virtual_res_id": self.purchases[0].id,
                },
                {
                    "of_type": "virtual",
                    "name": f"Request for Quotation - {self.purchases[1].name}.pdf",
                    "directory_id": self.purchase_directories[1].id,
                    "attachment_id": False,
                    "res_model": "purchase.order",
                    "of_virtual_res_model": self.env.ref("purchase.model_purchase_order").id,
                    "of_virtual_res_id": self.purchases[1].id,
                },
                {
                    "of_type": "virtual",
                    "name": f"Request for Quotation - {self.purchases[2].name}.pdf",
                    "directory_id": self.purchase_directories[2].id,
                    "attachment_id": False,
                    "res_model": "purchase.order",
                    "of_virtual_res_model": self.env.ref("purchase.model_purchase_order").id,
                    "of_virtual_res_id": self.purchases[2].id,
                },
            ],
        )

    def test_03_create_real_files_purchase(self):
        """Test that the real files are correctly created"""
        self.assertRecordValues(
            self.real_files,
            [
                {
                    "of_type": "real",
                    "name": "test.txt",
                    "directory_id": self.purchase_directories[0].id,
                    "attachment_id": self.attachments[0].id,
                    "res_model": "purchase.order",
                },
                {
                    "of_type": "real",
                    "name": "test-2.txt",
                    "directory_id": self.purchase_directories[1].id,
                    "attachment_id": self.attachments[1].id,
                    "res_model": "purchase.order",
                },
                {
                    "of_type": "real",
                    "name": "test-3.txt",
                    "directory_id": self.purchase_directories[2].id,
                    "attachment_id": self.attachments[2].id,
                    "res_model": "purchase.order",
                },
            ],
        )

    def test_04_update_directory_purchase(self):
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
                    "child_directory_ids": self.purchase_directories[0].ids,
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.purchase_directories[1].ids,
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.purchase_directories[2].ids,
                },
            ],
        )

    def test_05_update_subdirectory_purchase(self):
        """Test that the subdirectories are correctly updated"""
        self.assertRecordValues(
            self.purchase_directories,
            [
                {
                    "active": True,
                    "count_files": 2,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[0].id,
                        self.real_files[0].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Purchases",
                    "res_model": "purchase.order",
                    "parent_id": self.customer_a.of_dms_directory_id.id,
                    "of_code": False,
                },
                {
                    "active": True,
                    "count_files": 2,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[1].id,
                        self.real_files[1].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Purchases",
                    "res_model": "purchase.order",
                    "parent_id": self.supplier_a.of_dms_directory_id.id,
                    "of_code": False,
                },
                {
                    "active": True,
                    "count_files": 2,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[2].id,
                        self.real_files[2].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Purchases",
                    "res_model": "purchase.order",
                    "parent_id": self.supplier_b.of_dms_directory_id.id,
                    "of_code": False,
                },
            ],
        )
