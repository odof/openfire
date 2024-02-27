# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    of_is_reseller = fields.Boolean(string="Reseller", help="Check this box if this partner is a reseller.")
    of_is_installer = fields.Boolean(string="Installer", help="Check this box if this partner is a installer.")
    of_equipments_count = fields.Integer(string="Equipments count", compute='_compute_of_equipments_count')
    of_equipment_ids = fields.One2many(comodel_name='of.equipment', inverse_name='customer_id', string="Equipment")

    def _compute_of_equipments_count(self):
        for partner in self:
            partner.of_equipments_count = len(partner.of_equipment_ids)

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

    def name_get(self):
        """In an equipment, allows to choose partners who are not resellers/installers in parentheses."""
        is_reseller_prio = bool(self._context.get('of_is_reseller_prio'))
        is_installer_prio = bool(self._context.get('of_is_installer_prio'))
        if is_reseller_prio or is_installer_prio:
            result = []
            for employee in self:
                priority_display = (
                    is_reseller_prio and employee.of_is_reseller or is_installer_prio and employee.of_is_installer
                )
                result.append(
                    (
                        employee.id,
                        f"{'' if priority_display else '('}{employee.name}{'' if priority_display else ')'}",
                    )
                )
            return result
        return super().name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """In an equipment, displays resellers/installers first"""
        field_priority = False
        if self._context.get('of_is_reseller_prio'):
            field_priority = 'of_is_reseller'
        elif self._context.get('of_is_installer_prio'):
            field_priority = 'of_is_installer'
        if field_priority:
            args = args or []
            res = super().name_search(name, args + [[field_priority, '=', True]], operator, limit) or []
            limit = limit - len(res)
            res += super().name_search(name, args + [[field_priority, '=', False]], operator, limit) or []
            return res
        return super().name_search(name, args, operator, limit)
