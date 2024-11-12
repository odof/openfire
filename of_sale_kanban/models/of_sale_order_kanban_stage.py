# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFSaleOrderKanbanStage(models.Model):
    _name = 'of.sale.order.kanban.stage'
    _description = u"Étape kanban des bons de commande"
    _order = 'sequence, id'

    sequence = fields.Integer(string="Séquence", required=True, default=1)
    name = fields.Char(string="Nom de l'étape", required=True)
    color = fields.Integer()
