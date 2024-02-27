# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    of_equipment_ids = fields.Many2many(comodel_name='of.equipment', string="Equipments")
    of_equipments_count = fields.Integer(string="Equipments count", compute='_compute_of_equipments_count')

    def action_button_view_equipment(self):
        equipments = self.mapped('of_equipment_ids')
        action = self.env.ref('of_equipment.action_view_of_equipment').sudo().read()[0]
        if len(equipments) > 1:
            action['domain'] = [('id', 'in', equipments.ids)]
        elif len(equipments) == 1:
            action['views'] = [(self.env.ref('of_equipment.of_equipment_view_form').id, 'form')]
            action['res_id'] = equipments.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.depends('of_equipment_ids')
    def _compute_of_equipments_count(self):
        for move in self:
            move.of_equipments_count = len(move.of_equipment_ids)
