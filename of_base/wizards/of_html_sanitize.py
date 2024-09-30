# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OFHTMLSanitizeWizard(models.TransientModel):
    """HTML field cleaning wizard"""

    _name = "of.html.sanitize.wizard"
    _description = __doc__

    def action_button_clean(self):
        if not self.env.is_admin():
            raise UserError(_("Only the administrator is authorized to run this process."))

        _logger.info("HTML Sanitize Wizard - START")
        for model in self._get_models_to_html_sanitize():
            if model not in self.env:
                _logger.info(f"    -> Model: {model} - Not found")  # noqa
                continue

            _logger.info(f"    -> Model: {model}")  # noqa

            html_fields = [field for field in self.env[model]._fields.values() if field.type == "html" and field.store]

            for field in html_fields:
                _logger.info(f"            Field: {field.name}")
                records = self.env[model].with_context(active_test=False).search([(field.name, "ilike", "%img%")])
                count = 0
                for record in records:
                    record = record.with_prefetch()
                    if new_val := self.html_sanitize_img(record, record[field.name]):
                        record[field.name] = new_val
                        count += 1
                _logger.info(f"        Records: {count}")

        _logger.info("HTML Sanitize Wizard - END")
        return {"type": "ir.actions.act_window_close"}
