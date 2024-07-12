# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from .common import TestOFDMSPurchaseCommon


class TestOFDMSPurchaseResPartner(TestOFDMSPurchaseCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_create_subdirectory_purchase(self):
        """Test that the subdirectories are correctly created"""
        self.assertRecordValues(
            self.purchase_directories,
            [
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Purchases",
                    "res_model": "purchase.order",
                    "parent_id": self.customer_a.of_dms_directory_id.id,
                    "of_code": False,
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Purchases",
                    "res_model": "purchase.order",
                    "parent_id": self.supplier_a.of_dms_directory_id.id,
                    "of_code": False,
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Purchases",
                    "res_model": "purchase.order",
                    "parent_id": self.supplier_b.of_dms_directory_id.id,
                    "of_code": False,
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
                    "count_directories": 1,
                    "file_ids": [],
                    "child_directory_ids": self.purchase_directories[0].ids,
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 1,
                    "file_ids": [],
                    "child_directory_ids": self.purchase_directories[1].ids,
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 1,
                    "file_ids": [],
                    "child_directory_ids": self.purchase_directories[2].ids,
                },
            ],
        )
