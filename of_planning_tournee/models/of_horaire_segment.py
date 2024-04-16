# -*- coding: utf-8 -*-

from odoo import api, models


class OFHoraireSegment(models.Model):
    _inherit = 'of.horaire.segment'

    @api.model
    def recompute_is_full_tournee(self, employee_id, deb=False, fin=False):
        tournee_obj = self.env['of.planning.tournee']
        if not deb:
            tournees = tournee_obj.search([('employee_id', '=', employee_id)])
        else:
            tournees_domain = [('employee_id', '=', employee_id), ('date', '>=', deb)]
            tournees_domain = fin and tournees_domain + [('date', '<=', fin)] or tournees_domain
            tournees = tournee_obj.search(tournees_domain)
        tournees._compute_is_full()

    @api.model
    def create(self, vals):
        employee_id = vals.get('employee_id')
        deb = vals.get('date_deb')
        fin = vals.get('date_fin')
        res = super(OFHoraireSegment, self).create(vals)
        if employee_id:
            self.recompute_is_full_tournee(employee_id, deb, fin)
        return res

    @api.multi
    def write(self, vals):
        employee_id = vals.get('employee_id') or self.employee_id and self.employee_id.id
        deb = min(vals.get('date_deb', self.date_deb), self.date_deb)
        fin = max(vals.get('date_fin', self.date_fin), self.date_fin)
        res = super(OFHoraireSegment, self).write(vals)
        if employee_id:
            self.recompute_is_full_tournee(employee_id, deb, fin)
        return res

    @api.model
    def unlink(self):
        employee_id = self.employee_id and self.employee_id.id
        deb = self.date_deb
        fin = self.date_fin
        res = super(OFHoraireSegment, self).unlink()
        if employee_id:
            self.recompute_is_full_tournee(employee_id, deb, fin)
        return res
