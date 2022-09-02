# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, _


class CrmActivity(models.Model):
    _inherit = 'crm.activity'

    @api.model
    def _get_trigger_selection(self):
        selection = super(CrmActivity, self)._get_trigger_selection()
        return selection + [
            ('at_confirmation', _('At confirmation')),
        ]
