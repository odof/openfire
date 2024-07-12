# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from .common import TestOFDMSStockCommon


class TestOFDMSStockResPartner(TestOFDMSStockCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_create_subdirectory_stock(self):
        """Test that the subdirectories are correctly created"""
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
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Receipt Slips",
                    "res_model": "stock.picking",
                    "parent_id": self.customer_a.of_dms_directory_id.id,
                    "of_code": "outgoing",
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
                    "child_directory_ids": [],
                    "name": "Delivery Slips",
                    "res_model": "stock.picking",
                    "parent_id": self.supplier_a.of_dms_directory_id.id,
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
                    "parent_id": self.supplier_a.of_dms_directory_id.id,
                    "of_code": "outgoing",
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 0,
                    "file_ids": [],
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
                    "child_directory_ids": self.stock_directories[0:2].ids,
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 2,
                    "file_ids": [],
                    "child_directory_ids": self.stock_directories[2:4].ids,
                },
                {
                    "active": False,
                    "count_files": 0,
                    "count_directories": 2,
                    "file_ids": [],
                    "child_directory_ids": self.stock_directories[4:6].ids,
                },
            ],
        )
