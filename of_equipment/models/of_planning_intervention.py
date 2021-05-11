# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.addons.of_utils.models.of_utils import se_chevauchent
from odoo.exceptions import UserError, ValidationError

class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    equipment_ids = fields.Many2many(comodel_name='maintenance.equipment', string=u"Équipements", copy=False)
    verify_equipment = fields.Text(string=u"Équipement utilisé", compute='_compute_verify_equipment')
    verify_color = fields.Selection(selection=[
        ('red', 'Rouge'),
        ('grey', 'Gris'),
        ('none', 'Aucune')
        ], string="Couleur alerte", compute="_compute_verify_equipment")

    @api.depends('equipment_ids', 'date', 'employee_ids')
    def _compute_verify_equipment(self):
        for rdv in self:
            if rdv.equipment_ids and rdv.date:
                for equipment in rdv.equipment_ids:
                    interventions = equipment.equipment_not_available(rdv)
                    if interventions:
                        rdv.verify_color = 'red'
                        rdv.verify_equipment = u"Alerte : l'équipement %s est déjà utilisé sur ce créneau." % \
                                               equipment.name
                        continue
                    interventions = equipment.equipment_not_available(rdv, check_day=True)
                    if interventions and any([employee not in rdv.employee_ids for employee in interventions.mapped('employee_ids')]):
                        rdv.verify_color = 'grey'
                        rdv.verify_equipment = u"Attention : l'équipement %s est déjà utilisé pour une autre intervention à " \
                                               u"un autre moment de la journée, il pourrait ne pas être disponible" % \
                                               equipment.name
                        continue
                    rdv.verify_color = 'none'

    @api.model
    def create(self, vals):
        res = super(OfPlanningIntervention, self).create(vals)
        if res and res.equipment_ids:
            for equipment in res.equipment_ids:
                if equipment.equipment_not_available(res):
                    raise UserError(u"l'équipement %s est déjà utilisé pour une autre intervention aux "
                                    u"mêmes dates" % equipment.name)
        return res

    @api.multi
    def write(self, vals):
        res = super(OfPlanningIntervention, self).write(vals)
        for rdv in self:
            if rdv.equipment_ids and rdv.date:
                for equipment in rdv.equipment_ids:
                    if equipment.equipment_not_available(rdv):
                        raise UserError(u"l'équipement %s est déjà utilisé pour une autre intervention aux "
                                        u"mêmes dates" % equipment.name)
        return res


class OfService(models.Model):
    _inherit = 'of.service'

    equipment_ids = fields.Many2many(comodel_name='maintenance.equipment', string=u"Équipements")


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    of_intervention_ids = fields.Many2many(comodel_name='of.planning.intervention', string="Interventions")

    @api.multi
    def equipment_not_available(self, base_intervention, check_day=False):
        self.ensure_one()
        day = fields.Date.to_string(fields.Date.from_string(base_intervention.date))
        interventions = self.env['of.planning.intervention'].search([
            ('date_date', '=', day),
            ('equipment_ids', 'in', [self.id]),
            ('state', 'not in', ('cancel', 'postponed'))
        ])
        if base_intervention and base_intervention in interventions:
            interventions -= base_intervention
        if not interventions:
            return False
        if check_day and interventions:
            return interventions
        intervention = interventions.filtered(lambda i: se_chevauchent(i.date, i.date_deadline, base_intervention.date,
                                                                       base_intervention.date_deadline))
        if intervention:
            return intervention
        return False

