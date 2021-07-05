# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.addons.of_utils.models.of_utils import se_chevauchent
from odoo.exceptions import UserError, ValidationError


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    equipment_ids = fields.Many2many(
        comodel_name='maintenance.equipment', string=u"Équipements", copy=False,
        domain="['|', ('of_company_ids', '=', False), ('of_company_ids', 'in', company_id)]")
    verify_equipment = fields.Text(string=u"Équipement utilisé", compute='_compute_verify_equipment')
    verify_color = fields.Selection(selection=[
        ('red', 'Rouge'),
        ('grey', 'Gris'),
        ('none', 'Aucune')
        ], string="Couleur alerte", compute="_compute_verify_equipment")

    @api.depends('equipment_ids', 'date', 'employee_ids', 'date_deadline')
    def _compute_verify_equipment(self):
        for rdv in self:
            if rdv.equipment_ids and rdv.date:
                for equipment in rdv.equipment_ids:
                    # si il y a une différence c'est que nous sommes en train de modifier un record
                    # le compute est donc utilisé comme un onchange et il n'y a qu'un seul record dans self
                    if hasattr(self, '_origin') and self._origin != self:
                        interventions = equipment.with_context(from_id=self._origin.id).equipment_not_available(rdv)
                    else:
                        interventions = equipment.equipment_not_available(rdv)

                    if interventions:
                        rdv.verify_color = 'red'
                        rdv.verify_equipment = u"Alerte : l'équipement %s est déjà utilisé sur ce créneau." % \
                                               equipment.name
                        break
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

    equipment_ids = fields.Many2many(comodel_name='maintenance.equipment', string=u"Équipements",
                                     domain="['|', ('of_company_ids', '=', False), ('of_company_ids', '=', company_id)]")


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    of_intervention_ids = fields.Many2many(comodel_name='of.planning.intervention', string="Interventions")
    of_company_ids = fields.Many2many(comodel_name='res.company', string=u"Société(s)")

    @api.multi
    def equipment_not_available(self, base_intervention, check_day=False):
        self.ensure_one()
        # passage en sudo pour faire la vérification, les interventions étant en sudo cela ne pose pas de pb
        # pour afficher différentes informations des rdv trouvés
        # Si vérification réalisée sans le sudo on peut ne pas trouver des interventions avec le même équipement et
        # la même heure qui serait sur une autre société
        self = self.sudo()
        day = base_intervention.date_date
        domain = [
            ('date_date', '=', day),
            ('equipment_ids', 'in', [self.id]),
            ('state', 'not in', ('cancel', 'postponed')),
            ]
        if self.of_company_ids:
            domain.append(('company_id', 'in', self.of_company_ids.ids))
        if self._context.get('from_id'):
            domain.append(('id', 'not in', [self._context.get('from_id')]))
        interventions = self.env['of.planning.intervention'].search(domain)
        if base_intervention and base_intervention in interventions:
            interventions -= base_intervention
        if not interventions:
            return False
        if check_day and interventions:
            return interventions
        intervention = interventions.filtered(lambda i: se_chevauchent(i.date,
                                                                       i.date_deadline,
                                                                       base_intervention.date,
                                                                       base_intervention.date_deadline))
        if intervention:
            return intervention
        return False

