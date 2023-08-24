# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class OFMailTemplate(models.Model):
    _inherit = "of.mail.template"

    @api.model
    def _get_allowed_models(self):
        return super(OFMailTemplate, self)._get_allowed_models() + ['of.service']
