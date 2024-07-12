# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from .common import TestOFDMSCRMCommon


class TestOFDMSCRMCRMMove(TestOFDMSCRMCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leads = (
            cls.env["crm.lead"]
            .create(
                [
                    {
                        "name": "Lead 1",
                        "partner_id": False,
                    },
                    {
                        "name": "Lead 2",
                        "partner_id": cls.customer_a.id,
                        "company_id": cls.customer_a.company_id.id,
                    },
                    {
                        "name": "Lead 3",
                        "partner_id": cls.supplier_b.id,
                        "company_id": cls.supplier_b.company_id.id,
                    },
                ]
            )
            .sorted("id")
        )

        cls.attachments = cls.create_attachments(
            [
                {
                    "name": "test.txt",
                    "res_model": "crm.lead",
                    "res_id": cls.leads[0].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "crm.lead",
                    "res_id": cls.leads[1].id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "crm.lead",
                    "res_id": cls.leads[2].id,
                    "datas": cls.content_base64(),
                },
            ]
        ).sorted("id")

        cls.real_files = cls.file_model.search(
            [("of_type", "=", "real"), ("attachment_id", "in", cls.attachments.ids)]
        ).sorted("id")

    def test_01_create_attachment_crm(self):
        """Test that the attachment are correctly created"""
        self.assertRecordValues(
            self.attachments,
            [
                {
                    "name": "test.txt",
                    "res_model": "crm.lead",
                    "res_id": self.leads[0].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "crm.lead",
                    "res_id": self.leads[1].id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "crm.lead",
                    "res_id": self.leads[2].id,
                    "datas": self.content_base64(),
                },
            ],
        )

    def test_02_create_real_files_crm(self):
        """Test that the real files are correctly created"""
        self.assertRecordValues(
            self.real_files,
            [
                {
                    "of_type": "real",
                    "name": "test-2.txt",
                    "directory_id": self.crm_directories[0].id,
                    "attachment_id": self.attachments[1].id,
                    "res_model": "crm.lead",
                },
                {
                    "of_type": "real",
                    "name": "test-3.txt",
                    "directory_id": self.crm_directories[2].id,
                    "attachment_id": self.attachments[2].id,
                    "res_model": "crm.lead",
                },
            ],
        )

    def test_03_update_directory_crm(self):
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
                    "child_directory_ids": self.crm_directories[0].ids,
                },
                {
                    "active": False,
                    "count_directories": 0,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                },
                {
                    "active": True,
                    "count_directories": 1,
                    "count_files": 0,
                    "file_ids": [],
                    "child_directory_ids": self.crm_directories[2].ids,
                },
            ],
        )

    def test_04_update_subdirectory_crm(self):
        """Test that the subdirectories are correctly updated"""
        self.assertRecordValues(
            self.crm_directories,
            [
                {
                    "active": True,
                    "count_files": 1,
                    "count_directories": 0,
                    "file_ids": [
                        self.real_files[0].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Leads",
                    "res_model": "crm.lead",
                    "parent_id": self.customer_a.of_dms_directory_id.id,
                    "of_code": False,
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Leads",
                    "res_model": "crm.lead",
                    "parent_id": self.supplier_a.of_dms_directory_id.id,
                    "of_code": False,
                },
                {
                    "active": True,
                    "count_files": 1,
                    "count_directories": 0,
                    "file_ids": [
                        self.real_files[1].id,
                    ],
                    "child_directory_ids": [],
                    "name": "Leads",
                    "res_model": "crm.lead",
                    "parent_id": self.supplier_b.of_dms_directory_id.id,
                    "of_code": False,
                },
            ],
        )
