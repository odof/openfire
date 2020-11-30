# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.multi
    def action_pos_session_close(self):
        return super(PosSession, self.with_context(round=1)).action_pos_session_close()
