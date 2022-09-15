# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import requests
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    status_code = fields.Char(string='Post status code', default=False)

    @api.multi
    def _synchronize_status_code(self):
        for rec in self:
            payload = {'order_id': rec.id}
            r = requests.get('https://my.external.api/order', params=payload)
            rec.status_code = r.json()['code'] if r.status_code == 200 else False
