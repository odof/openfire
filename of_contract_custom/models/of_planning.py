# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.of_utils.models.of_utils import format_date


class OfPlanningPlannification(models.AbstractModel):
    _name = 'of.planning.plannification'

    nbr_interv = fields.Integer(string="Nombre de visites", help=u"Nombre de RDV d'interventions dans l'année", required=True)
    mois_reference_ids = fields.Many2many(comodel_name='of.mois', string=u"Mois de visite", required=True)
    tache_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche", required=True)

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

    @api.model
    def _domain_employee_ids(self):
        return [('of_est_intervenant', '=', True)]

    type_id = fields.Many2one(
        comodel_name='of.service.type', string="Type", required=True,)
    partner_code_magasin = fields.Char(string="Code magasin", related="partner_id.of_code_magasin", readonly=True)
    supplier_id = fields.Many2one(comodel_name='res.partner', string="Prestataire", domain="[('supplier','=',True)]")
    contract_id = fields.Many2one(comodel_name='of.contract', string="Contrat")
    contract_line_id = fields.Many2one(
        comodel_name='of.contract.line', string="Ligne de contrat",
        domain="['|','|',('contract_id','=',contract_id),('partner_id','=',partner_id),('address_id','=',address_id)]"
    )
    spec_date = fields.Char(string="Date", compute="_compute_spec_date")
    user_id = fields.Many2one(comodel_name='res.users', string="Utilisateur", default=lambda r:r.env.user)
    kanban_step_id = fields.Many2one(
        comodel_name='of.service.stage', string=u"Étapes kanban", group_expand='_read_group_stage_ids',
        domain="[('type_ids','=',type_id)]"
    )
    contract_message = fields.Char(string="Infos SAV du contrat", compute="_compute_contract_message")
    employee_ids = fields.Many2many(
        comodel_name='hr.employee', string="Intervenants", domain=lambda self: self._domain_employee_ids()
    )
    last_attachment_id = fields.Many2one(
        comodel_name='ir.attachment', string=u"Dernier rapport", compute="_compute_last_attachment_id"
    )

    @api.depends()
    def _compute_spec_date(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for service in self:
            interventions = service.intervention_ids.filtered(lambda i: i.state not in ('cancel', 'postponed'))
            if service.state == 'done' and interventions:
                service.spec_date = u"Réalisée le %s" % format_date(service.intervention_ids[-1].date_date, lang)
            elif interventions:
                service.spec_date = u"Prévue le %s" % format_date(service.intervention_ids[-1].date_date, lang)
            else:
                service.spec_date = u"Prévue entre %s et %s" % (format_date(service.date_next, lang), format_date(service.date_fin, lang))

    @api.depends('contract_line_id', 'contract_line_id.use_sav', 'type_id')
    def _compute_contract_message(self):
        sav_type = self.env.ref('of_contract_custom.of_contract_custom_type_sav', raise_if_not_found=False)
        if sav_type:
            for service in self:
                if service.type_id.id == sav_type.id and service.contract_line_id.use_sav:
                    count = service.contract_line_id.remaining_sav
                    service.contract_message = "%s SAV restant(s) pour cette ligne de contrat" % count
                elif service.type_id.id == sav_type.id and service.contract_line_id:
                    service.contract_message = "Cette ligne de contrat n'utilise pas l'option SAV"

    @api.depends()
    def _compute_last_attachment_id(self):
        """ Récupère le rapport 'Fiche d'intervention' du dernier RDV ayant la fiche d'intervention dans ses PJ"""
        attachment_obj = self.env['ir.attachment']
        for service in self:
            interventions = service.intervention_ids.filtered(lambda i: i.state not in ('cancel', 'postponed'))
            if interventions:
                for i in xrange(1, len(service.intervention_ids) + 1):
                    current_interv = service.intervention_ids[-i]
                    attachment = attachment_obj.search([('res_model', '=', 'of.planning.intervention'),
                                                        ('res_id', '=', current_interv.id),
                                                        ('of_intervention_report', '=', True)])
                    if attachment:
                        service.last_attachment_id = attachment[-1]
                        break

    @api.onchange('address_id', 'tache_id')
    def _onchange_address_id(self):
        super(OfService, self)._onchange_address_id()
        if self.address_id:
            if self.address_id.of_prestataire_id:
                self.supplier_id = self.address_id.of_prestataire_id

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        if self.contract_id and self.contract_id.partner_id:
            self.partner_id = self.contract_id.partner_id

    @api.onchange('contract_line_id')
    def onchange_contract_line_id(self):
        if self.contract_line_id and self.contract_line_id.address_id:
            self.address_id = self.contract_line_id.address_id
            self.parc_installe_id = self.contract_line_id.parc_installe_id

    @api.onchange('type_id')
    def onchange_type_id(self):
        if self.type_id and self.type_id.kanban_ids:
            self.kanban_step_id = self.type_id.kanban_ids[0]

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """
        Surcharge de la fonction pour afficher toutes les étapes existantes sur vue kanban
        """
        return stages.search([], order=order)

    @api.multi
    def get_action_view_intervention_context(self, action_context={}):
        if self.contract_line_id:
            action_context.update({'default_contract_line_id': self.contract_line_id.id})
            action_context.update({'default_employee_ids': [(6, 0, [emp.id for emp in self.employee_ids])]})
        return super(OfService, self).get_action_view_intervention_context(action_context)

    @api.multi
    def action_view_contract(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.action_contract').read()[0]
        action['domain'] = [('id', '=', self.contract_id.id)]
        return action

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
            action = self.env['of.popup.wizard'].popup_return(message=u"Aucun RDV d'intervention lié.")
        return action

    @api.multi
    def print_intervention_report(self):
        if self.intervention_ids:
            return self.env['report'].get_action(self.intervention_ids, 'of_planning.of_planning_fiche_intervention_report_template')
        else:
            return self.env['of.popup.wizard'].popup_return(message=u"Aucun RDV d'intervention lié.")

    @api.model
    def of_get_report_name(self, docs):
        return "Demande d'intervention"

    @api.model
    def of_get_report_number(self, docs):
        return ""

    @api.model
    def of_get_report_date(self, docs):
        if len(docs) == 1:
            lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
            return "%s " % format_date(docs.date_next, lang)
        return ""


class OfServiceType(models.Model):
    _name = 'of.service.type'

    name = fields.Char(string="Type de service")
    kanban_ids = fields.Many2many(comodel_name='of.service.stage', string=u"Étapes autorisées")


class OfServiceStage(models.Model):
    _name = 'of.service.stage'
    _order = 'sequence'

    name = fields.Char(string=u"Nom de l'étape")
    sequence = fields.Integer(string=u"Séquence")
    type_ids = fields.Many2many(comodel_name='of.service.type', string=u"Types autorisés")


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    contract_line_id = fields.Many2one(
        comodel_name='of.contract.line', string="Ligne de contrat",
        domain="service_id and [('service_ids','=',service_id)] or "
               "address_id and [('address_id','=',address_id)] or "
               "[]")
    contract_id = fields.Many2one(
            comodel_name='of.contract', string="Contrat",
            domain="service_id and [('service_ids','=',service_id)] or "
                   "partner_id and [('partner_id','=',partner_id)] or "
                   "address_id and [('partner_id','=',address_id)] or "
                   "[]")
    partner_code_magasin = fields.Char(string="Code magasin", related="partner_id.of_code_magasin", readonly=True)

    @api.onchange('contract_line_id')
    def _onchange_contract_line_id(self):
        if self.contract_line_id:
            self.contract_id = self.contract_line_id.contract_id
            self.address_id = self.contract_line_id.address_id or self.contract_line_id.partner_id

    @api.onchange('service_id')
    def _onchange_service_id(self):
        super(OfPlanningIntervention, self)._onchange_service_id()
        if self.service_id:
            self.contract_line_id = self.service_id.contract_line_id
            self.contract_id = self.service_id.contract_id
            if self.service_id.order_id:
                self.order_id = self.service_id.order_id


class Report(models.Model):
    _inherit = "report"

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        if report_name == 'of_planning.of_planning_fiche_intervention_report_template':
            self = self.with_context(copy_to_di=True, fiche_intervention=True)
        return super(Report, self).get_pdf(docids, report_name, html=html, data=data)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    of_intervention_report = fields.Boolean(string="Fiche d'intervention")

    def create(self, vals):
        if self._context.get('fiche_intervention'):
            vals['of_intervention_report'] = True
        attachment = super(IrAttachment, self).create(vals)
        if self._context.get('copy_to_di') and vals.get('res_model', '') == 'of.planning.intervention' \
           and vals.get('res_id') and isinstance(vals['res_id'], int):
            interv = self.env['of.planning.intervention'].browse(vals['res_id'])
            if interv.service_id:
                new_vals = vals.copy()
                new_vals['res_model'] = 'of.service'
                new_vals['res_id'] = interv.service_id.id
                self.env['ir.attachment'].create(new_vals)
        return attachment
