# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    of_internal = fields.Boolean(string=u"PJ interne")

    @api.model
    def check(self, mode, values=None):
        ids_to_exclude = []
        if self and mode == 'read' and self.env.user.has_group('base.group_user'):
            self._cr.execute('SELECT id FROM ir_attachment WHERE id IN %s AND of_internal', [self._ids])
            ids_to_exclude = [row[0] for row in self._cr.fetchall()]
        super(IrAttachment, self.filtered(lambda rec: rec.id not in ids_to_exclude)).check(mode, values=values)


