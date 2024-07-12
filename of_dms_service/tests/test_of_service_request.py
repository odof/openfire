# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import Command

from .common import TestOFDMSServiceCommon


class TestOFDMSServiceOFServiceRequest(TestOFDMSServiceCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.services = (
            cls.env["of.service.request"]
            .create(
                [
                    {
                        "partner_id": cls.customer_a.id,
                        "task_id": cls.task_installation.id,
                        "duration": 1,
                        "type_id": cls.env.ref("of_service.of_service_request_type_installation").id,
                        "company_id": cls.company_fr.id,
                        "employee_ids": [Command.set([cls.employee_tech_johnny.id])],
                    },
                    {
                        "partner_id": cls.supplier_a.id,
                        "task_id": cls.task_installation.id,
                        "duration": 1,
                        "type_id": cls.env.ref("of_service.of_service_request_type_installation").id,
                        "company_id": cls.company_fr.id,
                        "employee_ids": [Command.set([cls.employee_tech_johnny.id])],
                    },
                    {
                        "partner_id": cls.supplier_b.id,
                        "task_id": cls.task_installation.id,
                        "duration": 1,
                        "type_id": cls.env.ref("of_service.of_service_request_type_installation").id,
                        "company_id": cls.company_fr.id,
                        "employee_ids": [Command.set([cls.employee_tech_johnny.id])],
                    },
                ]
            )
            .sorted("id")
        )

        cls.attachments = cls.create_attachments(
            [
                {
                    "name": "test.txt",
                    "res_model": "of.service.request",
                    "res_id": cls.services[0].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "of.service.request",
                    "res_id": cls.services[1].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "of.service.request",
                    "res_id": cls.services[2].id,
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
                ("of_virtual_res_model", "=", cls.env.ref("of_service.model_of_service_request").id),
                ("of_virtual_res_id", "in", cls.services.ids),
            ]
        ).sorted("id")

    def test_01_create_attachment_service(self):
        """Test that the attachment are correctly created"""
        self.assertRecordValues(
            self.attachments,
            [
                {
                    "name": "test.txt",
                    "res_model": "of.service.request",
                    "res_id": self.services[0].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "of.service.request",
                    "res_id": self.services[1].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "of.service.request",
                    "res_id": self.services[2].id,
                    "datas": self.content_base64(),
                },
            ],
        )

    def test_02_create_virtual_files_service(self):
        """Test that the virtual files are correctly created"""
        self.assertRecordValues(
            self.virtual_files,
            [
                {
                    "of_type": "virtual",
                    "name": "Installation poêle à bois Partner A .pdf",
                    "directory_id": self.service_directories[0].id,
                    "attachment_id": False,
                    "res_model": "of.service.request",
                    "of_virtual_res_model": self.env.ref("of_service.model_of_service_request").id,
                    "of_virtual_res_id": self.services[0].id,
                },
                {
                    "of_type": "virtual",
                    "name": "Installation poêle à bois Supplier A .pdf",
                    "directory_id": self.service_directories[1].id,
                    "attachment_id": False,
                    "res_model": "of.service.request",
                    "of_virtual_res_model": self.env.ref("of_service.model_of_service_request").id,
                    "of_virtual_res_id": self.services[1].id,
                },
                {
                    "of_type": "virtual",
                    "name": "Installation poêle à bois Supplier B .pdf",
                    "directory_id": self.service_directories[2].id,
                    "attachment_id": False,
                    "res_model": "of.service.request",
                    "of_virtual_res_model": self.env.ref("of_service.model_of_service_request").id,
                    "of_virtual_res_id": self.services[2].id,
                },
            ],
        )

    def test_03_create_real_files_service(self):
        """Test that the real files are correctly created"""
        self.assertRecordValues(
            self.real_files,
            [
                {
                    "of_type": "real",
                    "name": "test.txt",
                    "directory_id": self.service_directories[0].id,
                    "attachment_id": self.attachments[0].id,
                    "res_model": "of.service.request",
                },
                {
                    "of_type": "real",
                    "name": "test-2.txt",
                    "directory_id": self.service_directories[1].id,
                    "attachment_id": self.attachments[1].id,
                    "res_model": "of.service.request",
                },
                {
                    "of_type": "real",
                    "name": "test-3.txt",
                    "directory_id": self.service_directories[2].id,
                    "attachment_id": self.attachments[2].id,
                    "res_model": "of.service.request",
                },
            ],
        )

    def test_04_update_directory_service(self):
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
                    "child_directory_ids": self.service_directories[0].ids,
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.service_directories[1].ids,
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.service_directories[2].ids,
                },
            ],
        )

    def test_05_update_subdirectory_service(self):
        """Test that the subdirectories are correctly updated"""
        self.assertRecordValues(
            self.service_directories,
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
                    "name": "Service Requests",
                    "res_model": "of.service.request",
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
                    "name": "Service Requests",
                    "res_model": "of.service.request",
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
                    "name": "Service Requests",
                    "res_model": "of.service.request",
                    "parent_id": self.supplier_b.of_dms_directory_id.id,
                    "of_code": False,
                },
            ],
        )
