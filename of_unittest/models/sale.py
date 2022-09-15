# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import time
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
        self._send_sale_to_external_service()
        for rec in self:
            rec.weekday_sms_sent = bool(is_weekday(datetime.now()))
        return res

    @api.multi
    def _send_sale_to_external_service(self):
        """ Envoie les informations de la commande à un service web externe. """
        for rec in self:
            for i in range(0, 5):
                print "Attention, je suis une fonction sensible à ne pas appeler dans un test unitaire"
                time.sleep(1)
