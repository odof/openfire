# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import os
from unittest import mock

import markupsafe

from odoo.addons.of_base.tests.common import TestOFBaseCommon


class TestOFHTMLSanitize(TestOFBaseCommon):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        openfire_png = os.path.join(os.path.dirname(__file__), '..', 'static', 'description', 'icon.png')
        with open(openfire_png, 'rb') as f:
            openfire_b64 = base64.b64encode(f.read()).decode('utf-8')
        cls.openfire_b64 = openfire_b64

    def _get_models_to_html_sanitize_without_res_partner(self):
        return ['account.move', 'crm.lead', 'project.task', 'sale.order']

    def _get_models_to_html_sanitize(self):
        return ['account.move', 'crm.lead', 'project.task', 'sale.order', 'res.partner']

    def test_01_html_sanitize_img(self):
        """Test that will sanitize hmtl if the model is in the list"""
        with mock.patch(
            'odoo.addons.of_base.models.base.Base._get_models_to_html_sanitize',
            return_value=self._get_models_to_html_sanitize(),
        ):
            partner = self.create_partner(
                {
                    'name': 'Test html sanitize',
                    'comment': f'<p>Test html sanitize</p><img src="data:image/png;base64,{self.openfire_b64}"/>',
                }
            )

            attachment = self.env['ir.attachment'].search(
                [('res_model', '=', 'res.partner'), ('res_id', '=', partner.id), ('of_internal', '=', True)]
            )

            self.assertEqual(len(attachment.ids), 1)
            self.assertEqual(
                partner.comment,
                markupsafe.Markup(f'<p>Test html sanitize</p><img src="/web/content/{attachment.id}">'),
            )

    def test_02_html_sanitize_img(self):
        """Test that will not sanitize hmtl if the model is not in the list"""
        with mock.patch(
            'odoo.addons.of_base.models.base.Base._get_models_to_html_sanitize',
            return_value=self._get_models_to_html_sanitize_without_res_partner(),
        ):
            partner = self.create_partner(
                {
                    'name': 'Test html sanitize',
                    'comment': f'<p>Test html sanitize</p><img src="data:image/png;base64,{self.openfire_b64}"/>',
                }
            )

            attachment = self.env['ir.attachment'].search(
                [('res_model', '=', 'res.partner'), ('res_id', '=', partner.id), ('of_internal', '=', True)]
            )

            self.assertEqual(len(attachment.ids), 0)
            self.assertEqual(
                partner.comment,
                markupsafe.Markup(f'<p>Test html sanitize</p><img src="data:image/png;base64,{self.openfire_b64}">'),
            )
