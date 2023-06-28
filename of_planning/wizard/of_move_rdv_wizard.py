# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFMoveRdvWizard(models.TransientModel):
    _name ='of.move.rdv.wizard'

    intervention_ids = fields.Many2many(comodel_name='of.planning.intervention', string=u"RDV(s)")
    employee_ids = fields.Many2many(comodel_name='hr.employee', string=u"Employé(s)", required=True)
    verif_dispo = fields.Boolean(string=u"Vérif chevauchement", default=True)
    forcer_dates = fields.Boolean(string=u"Forcer les dates")

    @api.multi
    def change_employee_for_interventions(self):
        self.ensure_one()
        base_vals = {
            'verif_dispo': self.verif_dispo,
            'employee_ids': [(6, 0, self.employee_ids._ids),],
        }
        if self.forcer_dates:
            base_vals['forcer_dates'] = True
            for intervention in self.intervention_ids:
                vals = base_vals.copy()
                vals['date_deadline_forcee'] = intervention.date_deadline
                intervention.write(vals)
        else:
            self.intervention_ids.write(base_vals)
