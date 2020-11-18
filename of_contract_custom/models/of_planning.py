# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.of_utils.models.of_utils import format_date

fo = {'daily': 'Jour(s)',
      'weekly': 'Semaine(s)',
      'monthly': 'Mois',
      'monthlylastday': 'Month(s) last day',
      'yearly': u'Année(s)'}


class OfPlanningPlannification(models.AbstractModel):
    _name = 'of.planning.plannification'

    nbr_interv = fields.Integer(string="Nombre de visites", help=u"Nombre de RDV d'interventions dans l'année", required=True)
    mois_reference_ids = fields.Many2many(comodel_name='of.mois', string=u"Mois de visite")
    tache_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche")

    @api.multi
    def _generate_services(self):
        """Fonction à implémenter pour générer les interventions à programmer"""
        raise NotImplementedError("A class inheriting from this one must implement '_generate_services' function")

    @api.onchange('mois_reference_ids', 'nbr_interv')
    def _onchange_mois_reference_ids(self):
        if self.mois_reference_ids and len(self.mois_reference_ids) > self.nbr_interv:
            raise UserError("Vous avez %s mois de visite pour %s visites" % (len(self.mois_reference_ids), self.nbr_interv or '0'))


class OfService(models.Model):
    _inherit = 'of.service'

    contract_id = fields.Many2one(comodel_name='of.contract', string="Contrat")
    contract_line_id = fields.Many2one(
        comodel_name='of.contract.line', string="Contrat")
    spec_date = fields.Char(string="Date", compute="_compute_spec_date")

    @api.depends()
    def _compute_spec_date(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for service in self:
            if service.state == 'done' and service.intervention_ids:
                service.spec_date = u"Réalisée le %s" % format_date(service.intervention_ids[-1].date_date, lang)
            if service.intervention_ids:
                service.spec_date = u"Prévue le %s" % format_date(service.intervention_ids[-1].date_date, lang)
            else:
                service.spec_date = u"Prévue entre %s et %s" % (format_date(service.date_next, lang), format_date(service.date_fin, lang))

    @api.multi
    def get_action_view_interventions_context(self, action_context={}):
        if self.contract_line_id:
            action_context.update({'default_contract_line_id': self.contract_line_id.id})
        return super(OfService, self).get_action_view_interventions_context(action_context)

    @api.multi
    def button_open_of_planning_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.of_contract_custom_open_interventions').read()[0]
        interventions = self.intervention_ids
        if len(interventions) > 1:
            action['context'] = {'search_default_service_id': self.id}
        elif len(interventions) == 1:
            action['views'] = [(self.env.ref('of_planning.of_planning_intervention_view_form').id, 'form')]
            action['res_id'] = interventions.ids[0]
        else:
            action = self.env['of.popup.wizard'].popup_return(message=u"Aucune intervention liée.")
        return action

    @api.multi
    def print_intervention_report(self):
        if self.intervention_ids:
            return self.env['report'].get_action(self.intervention_ids, 'of_planning.of_planning_fiche_intervention_report_template')
        else:
            return self.env['of.popup.wizard'].popup_return(message=u"Aucune intervention liée.")


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    contract_line_id = fields.Many2one(
        comodel_name='of.contract.line', string="Ligne de contrat",
        domain="service_id and [('service_ids', '=', service_id)] or "
               "address_id and [('address_id', '=', address_id)] or "
               "[]")

