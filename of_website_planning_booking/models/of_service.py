# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.addons.of_utils.models.of_utils import format_date
from odoo.exceptions import ValidationError, UserError


class OFService(models.Model):
    _inherit = 'of.service'

    @api.multi
    def website_planning_booking_name(self):
        self.ensure_one()
        service_obj = self.env['of.service']
        state = service_obj._fields['state'].convert_to_export(self.state, self)
        return u"%s - %s - %s" % (self.tache_id.name, self.number, state)
