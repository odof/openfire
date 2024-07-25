# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    of_tournee_ids = fields.One2many('of.planning.tournee', 'employee_id', string=u"Tournées")

    @api.multi
    def _get_start_return_address_changed(self, vals):
        def _compare_address(e, vals):
            if 'of_address_depart_id' in vals and vals['of_address_depart_id'] and \
                    e.of_address_depart_id != vals['of_address_depart_id']:
                return True
            return bool(
                'of_address_retour_id' in vals
                and vals['of_address_retour_id']
                and e.of_address_retour_id != vals['of_address_retour_id']
            )
        return self.filtered(lambda e: _compare_address(e, vals))

    @api.multi
    def write(self, vals):
        employees_address_changed = self._get_start_return_address_changed(vals)
        result = super(HrEmployee, self).write(vals)
        if employees_address_changed:
            tours_to_update = self.env['of.planning.tournee'].search([
                ('employee_id', 'in', employees_address_changed.ids),
                ('state', '!=', '3-confirmed'),
                ('date', '>=', fields.Date.today()),
            ])
            # write address on tours will trigger a recomputation of OSRM route
            tour_values = {}
            if 'of_address_depart_id' in vals and vals['of_address_depart_id']:
                tour_values['start_address_id'] = vals['of_address_depart_id']
            if 'of_address_retour_id' in vals and vals['of_address_retour_id']:
                tour_values['return_address_id'] = vals['of_address_retour_id']
            tour_values and tours_to_update and tours_to_update.write(tour_values)
        return result
