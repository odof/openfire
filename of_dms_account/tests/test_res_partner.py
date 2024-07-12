# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from .common import TestOFDMSAccountCommon


class TestOFDMSAccountResPartner(TestOFDMSAccountCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_create_subdirectory_account(self):
        """Test that the subdirectories are correctly created"""
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
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Customer Invoices & Refunds",
                    "res_model": "account.move",
                    "parent_id": self.customer_a.of_dms_directory_id.id,
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
        self.assertRecordValues(
            [
                self.customer_a.with_context({"active_test": False}).of_dms_directory_id,
                self.supplier_a.with_context({"active_test": False}).of_dms_directory_id,
                self.supplier_b.with_context({"active_test": False}).of_dms_directory_id,
            ],
            [
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 2,
                    "file_ids": [],
                    "child_directory_ids": self.account_directories[0:2].ids,
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 2,
                    "file_ids": [],
                    "child_directory_ids": self.account_directories[2:4].ids,
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 2,
                    "file_ids": [],
                    "child_directory_ids": self.account_directories[4:6].ids,
                },
            ],
        )
