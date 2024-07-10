# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_equipment_ids = fields.Many2many(comodel_name='of.equipment', string="Equipments", copy=False)
    of_equipments_count = fields.Integer(string="Equipments count", compute='_compute_of_equipments_data')
    of_equipment_id = fields.Many2one(comodel_name='of.equipment', string="Name", compute='_compute_of_equipments_data')
    of_equipment_address_id = fields.Many2one(
        comodel_name='res.partner', string="Installation Address", compute='_compute_of_equipments_data'
    )
    of_equipment_date = fields.Date(string="Installation Date", compute='_compute_of_equipments_data')
    of_equipment_note = fields.Text(string="Note", compute='_compute_of_equipments_data')

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
    def _compute_of_equipments_data(self):
        for order in self:
            # Default values
            of_equipment_id = False
            of_equipment_address_id = False
            of_equipment_date = False
            of_equipment_note = False
            order.of_equipments_count = len(order.of_equipment_ids)
            # If there is only one equipment, we take its data
            if order.of_equipments_count == 1:
                equipment = order.of_equipment_ids[0]
                of_equipment_id = equipment.id
                of_equipment_address_id = equipment.site_address_id.id
                of_equipment_date = equipment.installation_date
                of_equipment_note = equipment.note
            # Update the computed fields
            order.of_equipment_id = of_equipment_id
            order.of_equipment_address_id = of_equipment_address_id
            order.of_equipment_date = of_equipment_date
            order.of_equipment_note = of_equipment_note
