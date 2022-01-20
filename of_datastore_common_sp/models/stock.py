# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    of_datastore_move_id = fields.Integer(string=u"ID mouvement lié sur base connectée", copy=False)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_datastore_anomalie = fields.Boolean(string="En anomalie")
    of_datastore_id = fields.Integer(string=u"ID bon de transfert base connectée")
