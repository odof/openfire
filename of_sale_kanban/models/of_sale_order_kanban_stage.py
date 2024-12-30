# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSaleOrderKanbanStage(models.Model):
    _name = "of.sale.order.kanban.stage"
    _description = "Kanban stage for sales orders"
    _order = "sequence, id"

    sequence = fields.Integer(required=True, default=1)
    name = fields.Char(string="Stage name", required=True, translate=True)
