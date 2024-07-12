# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.of_dms.tests.common import TestOFDMSCommon
from odoo.addons.of_service.tests.common import TestOFServiceCommon

from ..hooks import post_init_hook


class TestOFDMSServiceCommon(TestOFDMSCommon, TestOFServiceCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        post_init_hook(cls.cr, cls.env)

        cls.service_directories = (
            cls.directory_model.with_context({"active_test": False})
            .search(
                [
                    ("res_model", "=", "of.service.request"),
                    (
                        "parent_id",
                        "in",
                        [
                            cls.customer_a.of_dms_directory_id.id,
                            cls.supplier_a.of_dms_directory_id.id,
                            cls.supplier_b.of_dms_directory_id.id,
                        ],
                    ),
                ]
            )
            .sorted("id")
        )
