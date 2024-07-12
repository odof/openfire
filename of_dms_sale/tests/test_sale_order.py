# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command

from .common import TestOFDMSSaleCommon


class TestOFDMSSaleSaleOrder(TestOFDMSSaleCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sales = (
            cls.env["sale.order"]
            .create(
                [
                    {
                        "partner_id": cls.customer_a.id,
                        "partner_invoice_id": cls.customer_a.id,
                        "partner_shipping_id": cls.customer_a.id,
                        "pricelist_id": cls.default_pricelist.id,
                        "fiscal_position_id": cls.fiscal_pos_5_5.id,
                        "user_id": cls.user_salesman.id,
                        "order_line": [
                            Command.create(
                                {
                                    "product_id": cls.product_consu_a.id,
                                    "product_uom_qty": 1,
                                    "tax_id": cls.tax_base,
                                    "price_unit": 50,
                                }
                            ),
                        ],
                    },
                    {
                        "partner_id": cls.supplier_a.id,
                        "partner_invoice_id": cls.supplier_a.id,
                        "partner_shipping_id": cls.supplier_a.id,
                        "pricelist_id": cls.default_pricelist.id,
                        "fiscal_position_id": cls.fiscal_pos_5_5.id,
                        "user_id": cls.user_salesman.id,
                        "order_line": [
                            Command.create(
                                {
                                    "product_id": cls.product_consu_a.id,
                                    "product_uom_qty": 1,
                                    "tax_id": cls.tax_base,
                                    "price_unit": 50,
                                }
                            ),
                        ],
                    },
                    {
                        "partner_id": cls.supplier_b.id,
                        "partner_invoice_id": cls.supplier_b.id,
                        "partner_shipping_id": cls.supplier_b.id,
                        "pricelist_id": cls.default_pricelist.id,
                        "fiscal_position_id": cls.fiscal_pos_5_5.id,
                        "user_id": cls.user_salesman.id,
                        "order_line": [
                            Command.create(
                                {
                                    "product_id": cls.product_consu_a.id,
                                    "product_uom_qty": 1,
                                    "tax_id": cls.tax_base,
                                    "price_unit": 50,
                                }
                            ),
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
                    "res_model": "sale.order",
                    "res_id": cls.sales[0].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "sale.order",
                    "res_id": cls.sales[1].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "sale.order",
                    "res_id": cls.sales[2].id,
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
                ("of_virtual_res_model", "=", cls.env.ref("sale.model_sale_order").id),
                ("of_virtual_res_id", "in", cls.sales.ids),
            ]
        ).sorted("id")

    def test_01_create_attachment_sale(self):
        """Test that the attachment are correctly created"""
        self.assertRecordValues(
            self.attachments,
            [
                {
                    "name": "test.txt",
                    "res_model": "sale.order",
                    "res_id": self.sales[0].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "sale.order",
                    "res_id": self.sales[1].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "sale.order",
                    "res_id": self.sales[2].id,
                    "datas": self.content_base64(),
                },
            ],
        )

    def test_02_create_virtual_files_sale(self):
        """Test that the virtual files are correctly created"""
        self.assertRecordValues(
            self.virtual_files,
            [
                {
                    "of_type": "virtual",
                    "name": f"Quotation - {self.sales[0].name}.pdf",
                    "directory_id": self.sale_directories[0].id,
                    "attachment_id": False,
                    "res_model": "sale.order",
                    "of_virtual_res_model": self.env.ref("sale.model_sale_order").id,
                    "of_virtual_res_id": self.sales[0].id,
                },
                {
                    "of_type": "virtual",
                    "name": f"Quotation - {self.sales[1].name}.pdf",
                    "directory_id": self.sale_directories[1].id,
                    "attachment_id": False,
                    "res_model": "sale.order",
                    "of_virtual_res_model": self.env.ref("sale.model_sale_order").id,
                    "of_virtual_res_id": self.sales[1].id,
                },
                {
                    "of_type": "virtual",
                    "name": f"Quotation - {self.sales[2].name}.pdf",
                    "directory_id": self.sale_directories[2].id,
                    "attachment_id": False,
                    "res_model": "sale.order",
                    "of_virtual_res_model": self.env.ref("sale.model_sale_order").id,
                    "of_virtual_res_id": self.sales[2].id,
                },
            ],
        )

    def test_03_create_real_files_sale(self):
        """Test that the real files are correctly created"""
        self.assertRecordValues(
            self.real_files,
            [
                {
                    "of_type": "real",
                    "name": "test.txt",
                    "directory_id": self.sale_directories[0].id,
                    "attachment_id": self.attachments[0].id,
                    "res_model": "sale.order",
                },
                {
                    "of_type": "real",
                    "name": "test-2.txt",
                    "directory_id": self.sale_directories[1].id,
                    "attachment_id": self.attachments[1].id,
                    "res_model": "sale.order",
                },
                {
                    "of_type": "real",
                    "name": "test-3.txt",
                    "directory_id": self.sale_directories[2].id,
                    "attachment_id": self.attachments[2].id,
                    "res_model": "sale.order",
                },
            ],
        )

    def test_04_update_directory_sale(self):
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
                    "child_directory_ids": self.sale_directories[0].ids,
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.sale_directories[1].ids,
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.sale_directories[2].ids,
                },
            ],
        )

    def test_05_update_subdirectory_sale(self):
        """Test that the subdirectories are correctly updated"""
        self.assertRecordValues(
            self.sale_directories,
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
                    "name": "Sales",
                    "res_model": "sale.order",
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
                    "name": "Sales",
                    "res_model": "sale.order",
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
                    "name": "Sales",
                    "res_model": "sale.order",
                    "parent_id": self.supplier_b.of_dms_directory_id.id,
                    "of_code": False,
                },
            ],
        )
