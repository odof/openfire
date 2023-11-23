# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    of_lastname = fields.Char(string=u"Nom", related='picking_partner_id.name', readonly=True)
    of_date_de_pose = fields.Date(
        string=u"Date de pose prévisionnelle", related='picking_id.sale_id.of_date_de_pose', readonly=True)
