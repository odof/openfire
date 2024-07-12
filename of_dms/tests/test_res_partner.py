# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.of_dms.tests.common import TestOFDMSCommon


class TestOFDMSRespartner(TestOFDMSCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_create_directory(self):
        """Test that the directories are correctly created"""
        self.assertRecordValues(
            [
                self.customer_a.of_dms_directory_id,
                self.supplier_a.of_dms_directory_id,
                self.supplier_b.of_dms_directory_id,
            ],
            [
                {
                    "name": "Partner A",
                    "parent_id": self.env.ref("of_dms.directory_contacts").id,
                    "active": False,
                    "res_model": "res.partner",
                    "res_id": self.customer_a.id,
                    "count_files": 0,
                    "file_ids": [],
                },
                {
                    "name": "Supplier A",
                    "parent_id": self.env.ref("of_dms.directory_contacts").id,
                    "active": False,
                    "res_model": "res.partner",
                    "res_id": self.supplier_a.id,
                    "count_files": 0,
                    "file_ids": [],
                },
                {
                    "name": "Supplier B",
                    "parent_id": self.env.ref("of_dms.directory_contacts").id,
                    "active": False,
                    "res_model": "res.partner",
                    "res_id": self.supplier_b.id,
                    "count_files": 0,
                    "file_ids": [],
                },
            ],
        )
