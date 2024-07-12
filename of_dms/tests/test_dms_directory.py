# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.of_dms.tests.common import TestOFDMSCommon


class TestOFDMSRespartner(TestOFDMSCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attachments = cls.create_attachments(
            [
                {
                    "name": "test.txt",
                    "res_model": cls.customer_a._name,
                    "res_id": cls.customer_a.id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": cls.supplier_b._name,
                    "res_id": cls.supplier_b.id,
                    "datas": cls.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": cls.supplier_b._name,
                    "res_id": cls.supplier_b.id,
                    "datas": cls.content_base64(),
                },
            ]
        )

        cls.files = cls.file_model.search([("attachment_id", "in", cls.attachments.ids)]).sorted("id")

    def test_01_create_attachment(self):
        """Test that the attachments are correctly created"""
        self.assertRecordValues(
            self.attachments,
            [
                {
                    "name": "test.txt",
                    "res_model": "res.partner",
                    "res_id": self.customer_a.id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-2.txt",
                    "res_model": "res.partner",
                    "res_id": self.supplier_b.id,
                    "datas": self.content_base64(),
                },
                {
                    "name": "test-3.txt",
                    "res_model": "res.partner",
                    "res_id": self.supplier_b.id,
                    "datas": self.content_base64(),
                },
            ],
        )

    def test_02_create_files(self):
        """Test that the files are correctly created"""
        self.assertRecordValues(
            self.files,
            [
                {
                    "of_type": "real",
                    "name": "test.txt",
                    "directory_id": self.customer_a.of_dms_directory_id.id,
                    "attachment_id": self.attachments[0].id,
                    "res_model": "res.partner",
                    "res_id": self.customer_a.id,
                },
                {
                    "of_type": "real",
                    "name": "test-2.txt",
                    "directory_id": self.supplier_b.of_dms_directory_id.id,
                    "attachment_id": self.attachments[1].id,
                    "res_model": "res.partner",
                    "res_id": self.supplier_b.id,
                },
                {
                    "of_type": "real",
                    "name": "test-3.txt",
                    "directory_id": self.supplier_b.of_dms_directory_id.id,
                    "attachment_id": self.attachments[2].id,
                    "res_model": "res.partner",
                    "res_id": self.supplier_b.id,
                },
            ],
        )

    def test_03_update_directory(self):
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
                    "count_files": 1,
                    "file_ids": self.files.filtered(
                        lambda f: f.attachment_id.id
                        in self.attachments.filtered(lambda att: att.res_id == self.customer_a.id).ids
                    ).ids,
                },
                {
                    "active": False,
                    "count_files": 0,
                    "file_ids": [],
                },
                {
                    "active": True,
                    "count_files": 2,
                    "file_ids": self.files.filtered(
                        lambda f: f.attachment_id.id
                        in self.attachments.filtered(lambda att: att.res_id == self.supplier_b.id).ids
                    ).ids,
                },
            ],
        )
