# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.addons.of_utils.models.of_utils import se_chevauchent
from odoo.exceptions import UserError, ValidationError

class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string=u"Équipement")
    verify_equipment = fields.Text(string=u"Équipement utilisé", compute='_compute_verify_equipment')

    @api.depends('equipment_id', 'date', 'employee_ids')
    def _compute_verify_equipment(self):
        for rdv in self:
            if rdv.equipment_id and rdv.date:
                interventions = rdv.equipment_id.equipment_not_available(rdv, dt=rdv.date, check_day=True)
                if interventions and any([employee not in rdv.employee_ids for employee in interventions.mapped('employee_ids')]):
                    rdv.verify_equipment = u"Attention : l'équipement %s est déjà utilisé pour une autre intervention à " \
                                           u"un autre moment de la journée, il pourrait ne pas être disponible" % \
                                           rdv.equipment_id.name

    @api.model
    def create(self, vals):
        equipment_id = vals.get('equipment_id', False)
        date = vals.get('date', False)
        if equipment_id and date:
            equipement = self.env['maintenance.equipment'].browse(equipment_id)
            if equipement.equipment_not_available(False, dt=date):
                raise UserError(u"l'équipement %s est déjà utilisé pour une autre intervention aux "
                                u"mêmes dates" % equipement.name)
        res = super(OfPlanningIntervention, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        res = super(OfPlanningIntervention, self).write(vals)
        for rdv in self:
            if rdv.equipment_id and rdv.date:
                if rdv.equipment_id.equipment_not_available(rdv, dt=rdv.date):
                    raise UserError(u"l'équipement %s est déjà utilisé pour une autre intervention aux "
                                    u"mêmes dates" % self.equipment_id.name)
        return res


class OfService(models.Model):
    _inherit = 'of.service'

    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string=u"Équipement")


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    of_intervention_ids = fields.One2many(comodel_name='of.planning.intervention', inverse_name='equipment_id', string="Interventions")

    @api.multi
    def equipment_not_available(self, base_intervention, dt=fields.Datetime.now(), check_day=False):
        self.ensure_one()
        day = fields.Date.to_string(fields.Date.from_string(dt))
        interventions = self.env['of.planning.intervention'].search([
            ('date_date', '=', day),
            ('equipment_id', '=', self.id)
            ])
        if base_intervention and base_intervention in interventions:
            interventions -= base_intervention
        if not interventions:
            return False
        if check_day and interventions:
            return interventions
        intervention = interventions.filtered(lambda i: se_chevauchent(i.date, i.date_deadline, dt, dt))
        if intervention:
            return intervention
        return False

