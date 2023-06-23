# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.addons.of_base.models.models import OF_MODELS_TO_SANITIZE

_logger = logging.getLogger(__name__)


class OFHTMLSanitizeWizard(models.TransientModel):
    _name = 'of.html.sanitize.wizard'
    _description = u"Assistant de nettoyage des champs HTML"

    @api.multi
    def process(self):
        if self._uid != SUPERUSER_ID:
            raise UserError(u"Seul l'administrateur est autorisé à lancer ce traitement !")

        _logger.info(u"HTML Sanitize Wizard - START")

        for model in OF_MODELS_TO_SANITIZE:

            _logger.info(u"HTML Sanitize Wizard - START - Model: %s" % model)

            html_fields = [
                field for field in self.env[model]._fields.itervalues() if field.type == 'html' and field.store]

            for field in html_fields:

                _logger.info(u"HTML Sanitize Wizard - START - Model: %s - Field: %s" % (model, field.name))

                records = self.env[model].with_context(active_test=False).search([(field.name, 'ilike', '%img%')])

                count = 0
                for record in records:
                    record = record.with_prefetch()
                    new_val = self.html_sanitize_img(record, record[field.name])
                    if new_val:
                        record[field.name] = new_val
                        count += 1

                _logger.info(
                    u"HTML Sanitize Wizard - END - Model: %s - Field: %s - Records: %s" % (model, field.name, count))

            _logger.info(u"HTML Sanitize Wizard - END - Model: %s" % model)

        _logger.info(u"HTML Sanitize Wizard - END")

        return {'type': 'ir.actions.act_window_close'}
