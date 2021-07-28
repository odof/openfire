# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_former = fields.Boolean(string="Is former")
    is_participant = fields.Boolean(string="Is participant", compute="_compute_is_participant", search="_search_is_participant")


    def _compute_is_participant(self):
        for partner in self:
            session_line_obj = self.env['of.training.session.line']
            partner.is_participant = bool(session_line_obj.search_count([['participant_ids','in',partner.ids]]))

    @api.multi
    def _search_is_participant(self, operator, value):
        field_id = self.search([]).filtered(lambda x: x.is_participant == value)
        return [('id', operator, [x.id for x in field_id] if field_id else False)]