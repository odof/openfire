# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import base64

from odoo.tests import tagged

from odoo.addons.of_base.tests.common import TestOFBaseCommon


@tagged("openfire_dms")
class TestOFDMSCommon(TestOFBaseCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.access_group_model = cls.env["dms.access.group"]
        cls.storage_model = cls.env["dms.storage"]
        cls.directory_model = cls.env["dms.directory"]
        cls.file_model = cls.env["dms.file"]
        cls.category_model = cls.env["dms.category"]
        cls.tag_model = cls.env["dms.tag"]
        cls.attachment_model = cls.env["ir.attachment"]
        cls.virtual_file_report_model = cls.env["of.dms.virtual_file_report"]

    @classmethod
    def content_base64(cls):
        return base64.b64encode(b"\xff data")

    @classmethod
    def create_attachments(cls, vals_list):
        attachments = cls.attachment_model.create(vals_list)
        return attachments
