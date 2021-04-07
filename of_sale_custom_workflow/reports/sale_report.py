# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    of_custom_confirmation_date = fields.Datetime(string=u"Date de confirmation", readonly=True)
    of_confirmation_date = fields.Datetime(string=u"Date d'enregistrement")

    def _select(self):
        res = super(SaleReport, self)._select()
        res += """
            , s.of_custom_confirmation_date AS of_custom_confirmation_date
        """
        return res

    def _group_by(self):
        res = super(SaleReport, self)._group_by()
        res += ", s.of_custom_confirmation_date"
        return res
