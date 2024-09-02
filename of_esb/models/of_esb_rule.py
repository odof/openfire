# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESBRule(models.Model):
    _name = 'of.esb.rule'

    name = fields.Char()
    channel_bus = fields.Char(required=True, string="Channel")
    type_bus = fields.Many2one(comodel_name='of.esb.type.bus', required=True, string="Type of bus")
    service = fields.Many2one(comodel_name='of.esb.service', required=True)
    ttype = fields.Selection([('user', 'user'), ('system', 'system')], string="Type", default="user")

    def unlink(self):
        # on ne peut pas supprimer une rule system, juste les "user"
        return super(ESBRule, self.filtered(lambda r: r.ttype == "user")).unlink()
