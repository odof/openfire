# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    of_canvasser_id = fields.Many2one(comodel_name='res.users', string=u"Prospecteur", readonly=True)

    def _select(self):
        res = super(SaleReport, self)._select()
        res += ", s.of_canvasser_id as of_canvasser_id"
        return res

    def _group_by(self):
        res = super(SaleReport, self)._group_by()
        res += ", s.of_canvasser_id"
        return res
