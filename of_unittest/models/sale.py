# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime
from odoo import api, models, fields


def is_weekday(order_date):
    return (0 <= order_date.weekday() < 5)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    weekday_sms_sent = fields.Boolean(string='Weekday SMS sent')

    @api.multi
    def action_confirm(self):
        """ Surcharge de la fonction d'origine pour ajouter un appel à un service web sensible. """
        res = super(SaleOrder, self).action_confirm()
        for rec in self:
            rec.weekday_sms_sent = bool(is_weekday(datetime.now()))
        return res
