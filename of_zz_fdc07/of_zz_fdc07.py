# -*- coding: utf-8 -*-

from openerp import models, fields, api


class res_partner(models.Model):
    _inherit = 'res.partner'

    of_service = fields.Char(u'Service', size=64)

    @api.one
    def copy(self, default=None):
        default = dict(default or {}, meeting_ids=[])
        return super(res_partner, self).copy(default)
