# -*- encoding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class OFServiceCreateInterventionWizard(models.TransientModel):
    _name = 'of.service.create.intervention.wizard'
    _description = u"Assistant de création de RDV depuis les DI"

    employee_id = fields.Many2one(comodel_name='hr.employee', string=u"Intervenant")
    start_date = fields.Datetime(string=u"Date de début")
    line_ids = fields.One2many(
        comodel_name='of.service.create.intervention.line.wizard', inverse_name='wizard_id', string=u"Lignes")
    show_warning = fields.Boolean(string=u"Avertissement", compute='_compute_show_warning')

    @api.depends('employee_id', 'start_date', 'line_ids')
    def _compute_show_warning(self):
        for rec in self:
            if rec.employee_id and rec.start_date and rec.line_ids:
                start_date = fields.Datetime.from_string(self.start_date)
                end_date = start_date
                for service in rec.line_ids.mapped('service_id'):
                    end_date += relativedelta(hours=service.duree)
                rdv = self.env['of.planning.intervention'].search(
                    [('employee_ids', 'in', self.employee_id.id),
                     ('date', '<', fields.Datetime.to_string(end_date)),
                     ('date_deadline', '>', fields.Datetime.to_string(start_date)),
                     ('state', 'not in', ['cancel', 'postponed'])], limit=1)
                if rdv:
                    rec.show_warning = True
                    continue
            rec.show_warning = False

    @api.multi
    def action_create_intervention(self):
        self.ensure_one()

        intervention_obj = self.env['of.planning.intervention']
        new_interventions = self.env['of.planning.intervention']
        group_flex = self.env.user.has_group('of_planning.of_group_planning_intervention_flexibility')
        if not self._context.get('tz'):
            self = self.with_context(tz='Europe/Paris')

        current_date = fields.Datetime.from_string(self.start_date)

        for service in self.line_ids.mapped('service_id'):

            end_date = current_date + relativedelta(hours=service.duree)

            if service.address_id:
                name = [service.address_id.name_get()[0][1]]
                for field in ('zip', 'city'):
                    val = getattr(service.address_id, field)
                    if val:
                        name.append(val)
            name = name and " ".join(name) or "Intervention"

            values = {
                'partner_id': service.partner_id.id,
                'address_id': service.address_id.id,
                'tache_id': service.tache_id.id,
                'template_id': service.template_id.id,
                'service_id': service.id,
                'employee_ids': [(4, self.employee_id.id)],
                'tag_ids': [(4, tag.id) for tag in service.tag_ids],
                'date': fields.Datetime.to_string(current_date),
                'date_deadline_forcee': fields.Datetime.to_string(end_date),
                'duree': service.duree,
                'forcer_dates': True,
                'verif_dispo': False,
                'name': name,
                'user_id': self._uid,
                'company_id': service.company_id.id,
                'description_interne': service.note,
                'order_id': service.order_id.id,
                'origin_interface': u"Générer RDV depuis DI",
                'flexible': service.tache_id.flexible,
            }

            intervention = intervention_obj.create(values)
            if group_flex:
                others = intervention.get_overlapping_intervention().filtered('flexible')
                if others:
                    others.button_postponed()
            intervention.onchange_company_id()
            intervention.with_context(of_import_service_lines=True)._onchange_service_id()
            intervention.with_context(of_import_service_lines=True)._onchange_tache_id()
            intervention.with_context(of_import_service_lines=True).onchange_template_id()
            new_interventions += intervention

            current_date = end_date

        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]
        context = safe_eval(action['context'])
        context['force_date_start'] = new_interventions[0].date_date
        action['context'] = str(context)
        action['domain'] = [('id', 'in', new_interventions.ids)]
        return action


class OFServiceCreateInterventionLineWizard(models.TransientModel):
    _name = 'of.service.create.intervention.line.wizard'
    _description = u"Ligne d'assistant de création de RDV depuis les DI"
    _order = 'sequence'

    wizard_id = fields.Many2one(comodel_name='of.service.create.intervention.wizard', string=u"Wizard")
    sequence = fields.Integer(string=u"Séquence", default=10)
    service_id = fields.Many2one(comodel_name='of.service', string=u"DI", required=True)
    service_number = fields.Char(string=u"Numéro", related='service_id.number')
    service_titre = fields.Char(string=u"Titre", related='service_id.titre')
    service_partner_id = fields.Many2one(
        comodel_name='res.partner', string=u"Partenaire", related='service_id.partner_id')
    service_address_zip = fields.Char(string=u"Code postal", related='service_id.address_zip')
    service_address_city = fields.Char(string=u"Ville", related='service_id.address_city')
    service_task_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche", related='service_id.tache_id')
