# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command

from .common import TestOFDMSAccountCommon


class TestOFDMSAccountAccountMove(TestOFDMSAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.moves = (
            cls.env["account.move"]
            .create(
                [
                    {
                        "move_type": "out_invoice",
                        "partner_id": cls.customer_a.id,
                        "company_id": cls.company_fr.id,
                        "invoice_line_ids": [
                            Command.create(
                                {
                                    "product_id": cls.product_wood_stove.id,
                                    "quantity": 1,
                                    "price_unit": 50,
                                }
                            )
                        ],
                    },
                    {
                        "move_type": "in_invoice",
                        "partner_id": cls.supplier_a.id,
                        "company_id": cls.company_fr.id,
                        "invoice_line_ids": [
                            Command.create(
                                {
                                    "product_id": cls.product_wood_stove.id,
                                    "quantity": 1,
                                    "price_unit": 1000,
                                }
                            )
                        ],
                    },
                    {
                        "move_type": "in_refund",
                        "partner_id": cls.supplier_a.id,
                        "company_id": cls.company_fr.id,
                        "invoice_line_ids": [
                            Command.create(
                                {
                                    "product_id": cls.product_wood_stove.id,
                                    "quantity": 1,
                                    "price_unit": 1000,
                                }
                            )
                        ],
                    },
                ]
            )
            .sorted("id")
        )

        cls.attachments = cls.create_attachments(
            [
                {
                    "name": "test.txt",
                    "res_model": "account.move",
                    "res_id": cls.moves[0].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "account.move",
                    "res_id": cls.moves[2].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "account.move",
                    "res_id": cls.moves[2].id,
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
                ("of_virtual_res_model", "=", cls.env.ref("account.model_account_move").id),
                ("of_virtual_res_id", "in", cls.moves.ids),
            ]
        ).sorted("id")

    def test_01_create_attachment_account(self):
        """Test that the attachment are correctly created"""
        self.assertRecordValues(
            self.attachments,
            [
                {
                    "name": "test.txt",
                    "res_model": "account.move",
                    "res_id": self.moves[0].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "account.move",
                    "res_id": self.moves[2].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "account.move",
                    "res_id": self.moves[2].id,
                    "datas": self.content_base64(),
                },
            ],
        )

    def test_02_create_virtual_files_account(self):
        """Test that the virtual files are correctly created"""
        self.assertRecordValues(
            self.virtual_files,
            [
                {
                    "of_type": "virtual",
                    "name": "Facture brouillon FAC_2024_00001.pdf",
                    "directory_id": self.account_directories[1].id,
                    "attachment_id": False,
                    "res_model": "account.move",
                    "of_virtual_res_model": self.env.ref("account.model_account_move").id,
                    "of_virtual_res_id": self.moves[0].id,
                },
                {
                    "of_type": "virtual",
                    "name": "Facture brouillon FACTU_2024_10_0001.pdf",
                    "directory_id": self.account_directories[2].id,
                    "attachment_id": False,
                    "res_model": "account.move",
                    "of_virtual_res_model": self.env.ref("account.model_account_move").id,
                    "of_virtual_res_id": self.moves[1].id,
                },
                {
                    "of_type": "virtual",
                    "name": "Avoir fournisseur brouillon RFACTU_2024_10_0001.pdf",
                    "directory_id": self.account_directories[2].id,
                    "attachment_id": False,
                    "res_model": "account.move",
                    "of_virtual_res_model": self.env.ref("account.model_account_move").id,
                    "of_virtual_res_id": self.moves[2].id,
                },
            ],
        )

    def test_03_create_real_files_account(self):
        """Test that the real files are correctly created"""
        self.assertRecordValues(
            self.real_files,
            [
                {
                    "of_type": "real",
                    "name": "test.txt",
                    "directory_id": self.account_directories[1].id,
                    "attachment_id": self.attachments[0].id,
                    "res_model": "account.move",
                },
                {
                    "of_type": "real",
                    "name": "test-2.txt",
                    "directory_id": self.account_directories[2].id,
                    "attachment_id": self.attachments[1].id,
                    "res_model": "account.move",
                },
                {
                    "of_type": "real",
                    "name": "test-3.txt",
                    "directory_id": self.account_directories[2].id,
                    "attachment_id": self.attachments[2].id,
                    "res_model": "account.move",
                },
            ],
        )

    def test_04_update_directory_account(self):
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
                    "child_directory_ids": self.account_directories[1].ids,
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.account_directories[2].ids,
                },
                {
                    "active": False,
                    "count_directories": 0,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                },
            ],
        )

    def test_05_update_subdirectory_account(self):
        """Test that the subdirectories are correctly updated"""
        self.assertRecordValues(
            self.account_directories,
            [
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Vendor Invoices & Refunds",
                    "res_model": "account.move",
                    "parent_id": self.customer_a.of_dms_directory_id.id,
                    "of_code": "IN",
                },
                {
                    "active": True,
                    "count_files": 2,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[0].id,
                        self.real_files[0].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Customer Invoices & Refunds",
                    "res_model": "account.move",
                    "parent_id": self.customer_a.of_dms_directory_id.id,
                    "of_code": "OUT",
                },
                {
                    "active": True,
                    "count_files": 4,
                    "count_directories": 0,
                    "file_ids": [
                        self.virtual_files[1].id,
                        self.virtual_files[2].id,
                        self.real_files[1].id,
                        self.real_files[2].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Vendor Invoices & Refunds",
                    "res_model": "account.move",
                    "parent_id": self.supplier_a.of_dms_directory_id.id,
                    "of_code": "IN",
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Customer Invoices & Refunds",
                    "res_model": "account.move",
                    "parent_id": self.supplier_a.of_dms_directory_id.id,
                    "of_code": "OUT",
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Vendor Invoices & Refunds",
                    "res_model": "account.move",
                    "parent_id": self.supplier_b.of_dms_directory_id.id,
                    "of_code": "IN",
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Customer Invoices & Refunds",
                    "res_model": "account.move",
                    "parent_id": self.supplier_b.of_dms_directory_id.id,
                    "of_code": "OUT",
                },
            ],
        )
