# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class OfService(models.Model):
    _inherit = "of.service"

    parc_installe_id = fields.Many2one(comodel_name='of.parc.installe', string=u"No de série")
    parc_installe_product_id = fields.Many2one(
        'product.product', string=u"Désignation", related="parc_installe_id.product_id", readonly=True)
    parc_installe_site_adresse_id = fields.Many2one(
        'res.partner', string=u"Adresse de pose", related="parc_installe_id.site_adresse_id", readonly=True)
    parc_installe_note = fields.Text(string=u"Note", related="parc_installe_id.note", readonly=True)
    sav_id = fields.Many2one(
        "project.issue", string="SAV", domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")
    parc_type_garantie = fields.Selection(related='parc_installe_id.type_garantie')

    of_categorie_id = fields.Many2one('of.project.issue.categorie', string=u"Catégorie", ondelete='restrict')
    of_canal_id = fields.Many2one('of.project.issue.canal', string=u"Canal", ondelete='restrict')
    payer_mode = fields.Selection([
        ('client', u"Client"),
        ('retailer', u"Revendeur"),
        ('manufacturer', u"Fabricant"),
    ], string=u"Payeur")

    in_progress_datetime = fields.Datetime(string=u"Date de début de prise en charge", copy=False)
    done_datetime = fields.Datetime(string=u"Date de fin de prise en charge", copy=False)
    in_progress_time = fields.Float(
        string=u"Temps de prise en compte (heures)", compute='_compute_in_progress_time', store=True,
        group_operator="avg")
    done_time = fields.Float(
        string=u"Temps de gestion (heures)", compute='_compute_done_time', store=True, group_operator="avg")
    installation_date = fields.Date(string=u"Date de pose", related='parc_installe_id.date_installation', readonly=True)

    @api.depends('parc_installe_id.intervention_ids', 'address_id.intervention_address_ids',
                 'partner_id.intervention_address_ids')
    def _compute_historique_interv_ids(self):
        for service in self:
            if service.parc_installe_id:
                service.historique_interv_ids = service.parc_installe_id.intervention_ids
            else:
                super(OfService, self)._compute_historique_interv_ids()

    @api.depends('create_date', 'in_progress_datetime')
    def _compute_in_progress_time(self):
        for service in self:
            if service.create_date and service.in_progress_datetime:
                duration = fields.Datetime.from_string(service.in_progress_datetime) - fields.Datetime.from_string(
                    service.create_date)
                service.in_progress_time = duration.total_seconds() / 3600.0
            else:
                service.in_progress_time = 0.0

    @api.depends('create_date', 'done_datetime')
    def _compute_done_time(self):
        for service in self:
            if service.create_date and service.done_datetime:
                duration = fields.Datetime.from_string(service.done_datetime) - fields.Datetime.from_string(
                    service.create_date)
                service.done_time = duration.total_seconds() / 3600.0
            else:
                service.done_time = 0.0

    @api.onchange('address_id')
    def _onchange_address_id(self):
        self.ensure_one()
        super(OfService, self)._onchange_address_id()
        if self.address_id and (not self.parc_installe_id or self.parc_installe_site_adresse_id != self.address_id):
            parc_obj = self.env['of.parc.installe']
            if not parc_obj.check_access_rights('read', raise_exception=False):
                # ne pas tenter le onchange si n'a pas les droits
                return
            parc_installe = parc_obj.search([('site_adresse_id', '=', self.address_id.id)], limit=1)
            if not parc_installe:
                parc_installe = parc_obj.search([('client_id', '=', self.address_id.id)], limit=1)
            if not parc_installe and self.partner_id:
                parc_installe = parc_obj.search([('client_id', '=', self.partner_id.id)], limit=1)
            if parc_installe:
                self.parc_installe_id = parc_installe

    @api.onchange('sav_id')
    def _onchange_sav_id(self):
        self.ensure_one()
        if self.sav_id:
            self.date_fin = self.get_fin_date()

    @api.multi
    def get_fin_date(self, date_str=False):
        """
        :param date_str: Date de prochaine planif à utiliser pour le calcul, sous format string
        :return: Date à partir de laquelle l'intervention passe à l'état 'en retard'
        :rtype string
        """
        self.ensure_one()
        date_next_str = date_str or self.date_next or False

        if date_next_str:
            date_fin = fields.Date.from_string(date_next_str)
            if (not self.tache_id or not self.tache_id.fourchette_planif) and self.sav_id:
                # une semaine par défaut pour les SAV
                date_fin += relativedelta(weeks=1)
                date_fin -= relativedelta(days=1)
                # ^- moins 1 jour car les intervalles de dates sont inclusifs
                return fields.Date.to_string(date_fin)
            else:
                return super(OfService, self).get_fin_date(date_next_str)
        else:
            return ""

    @api.multi
    def get_action_view_intervention_context(self, context={}):
        context = super(OfService, self).get_action_view_intervention_context(context)
        context['default_parc_installe_id'] = self.parc_installe_id and self.parc_installe_id.id or False
        context['default_sav_id'] = self.sav_id and self.sav_id.id or False
        return context

    @api.multi
    def write(self, vals):
        res = super(OfService, self).write(vals)
        if vals.get('kanban_step_id'):
            step = self.env['of.service.stage'].browse(vals.get('kanban_step_id'))
            if step and step.state == 'open':
                for service in self.filtered(lambda s: not s.in_progress_datetime):
                    service.in_progress_datetime = fields.Datetime.now()
            if step and step.state == 'done':
                for service in self.filtered(lambda s: not s.done_datetime):
                    service.done_datetime = fields.Datetime.now()
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        res = super(OfService, self)._read_group_stage_ids(stages, domain, order)
        if self._context.get('of_kanban_steps') == 'SAV':
            sav_type = self.env.ref('of_service_parc_installe.of_service_type_sav', raise_if_not_found=False)
            if sav_type:
                return res.filtered(lambda s: sav_type.id in s.type_ids.ids)
        return res


class OFServiceStage(models.Model):
    _inherit = 'of.service.stage'

    state = fields.Selection(selection=[
        ('draft', u"Nouveau"),
        ('open', u"En cours"),
        ('pending', u"En attente"),
        ('done', u"Terminé"),
        ('cancelled', u"Annulé")], string=u"État")


class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    parc_installe_id = fields.Many2one(
        'of.parc.installe', string=u"Parc installé",
        domain="['|', '|', ('client_id', '=', partner_id), ('client_id', '=', address_id), "
               "('site_adresse_id', '=', address_id)]")
    parc_installe_product_name = fields.Char(
        string=u"Désignation", related="parc_installe_id.product_id.name", readonly=True)
    historique_parc_ids = fields.One2many(
        comodel_name='of.planning.intervention',
        compute="_compute_historique_parc_ids",
        string=u"Historique (parc installé"
        )

    @api.depends('partner_id', 'address_id', 'parc_installe_id')
    def _compute_historique_rdv_ids(self):
        # l'historique du parc installé se trouve dans un autre champ
        for interv in self:
            if interv.address_id:
                interventions = interv.address_id.intervention_address_ids
            elif interv.partner_id:
                interventions = interv.partner_id.intervention_partner_ids
            else:
                continue
            interv.historique_rdv_ids = self.search([
                ('id', 'in', interventions.ids),
                ('date_date', '<', interv.date_date),
                '|', ('parc_installe_id', '=', False), ('parc_installe_id', '!=', interv.parc_installe_id.id)
            ])

    @api.depends('parc_installe_id')
    def _compute_historique_parc_ids(self):
        for interv in self:
            if interv.parc_installe_id:
                interv.historique_parc_ids = interv.parc_installe_id.intervention_ids.filtered(
                    lambda i: interv.date_date > i.date_date)

    @api.onchange('address_id')
    def _onchange_address_id(self):
        super(OfPlanningIntervention, self)._onchange_address_id()
        if self.address_id and self.parc_installe_id.site_adresse_id != self.address_id and \
           not self._context.get('from_portal'):
            parc_installe = False
            parc_obj = self.env['of.parc.installe']
            if not parc_obj.check_access_rights('read', raise_exception=False):
                return
            # limit = 2 to limit the number of records fetched by the search, we just need to know if there is more
            # than one
            found_records = parc_obj.search([('site_adresse_id', '=', self.address_id.id)], limit=2)
            if not found_records:
                found_records = parc_obj.search([('client_id', '=', self.address_id.id)], limit=2)
            if not found_records and self.partner_id:
                found_records = parc_obj.search([('client_id', '=', self.partner_id.id)], limit=2)
            if found_records and len(found_records) == 1:
                parc_installe = found_records[0]
            self.parc_installe_id = parc_installe

    @api.model
    def create(self, vals):
        service_obj = self.env['of.service']
        service = vals.get('service_id') and service_obj.browse(vals['service_id'])
        if service and not vals.get('parc_installe_id'):
            parc = service.parc_installe_id
            vals['parc_installe_id'] = parc.id
        return super(OfPlanningIntervention, self).create(vals)

    @api.multi
    def button_open_of_planning_intervention(self):
        if self.ensure_one():
            return {
                'name': 'of.planning.intervention.form',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.planning.intervention',
                'res_id': self._ids[0],
                'type': 'ir.actions.act_window',
            }


class OfParcInstalle(models.Model):
    _inherit = "of.parc.installe"

    intervention_ids = fields.One2many('of.planning.intervention', 'parc_installe_id', string="Interventions")
    service_count = fields.Integer(compute="_compute_service_count")
    a_programmer_count = fields.Integer(compute="_compute_service_count")

    @api.multi
    def _compute_service_count(self):
        """Smart button vue parc installé : renvoi le nombre de service lié à la machine installée"""
        service_obj = self.env['of.service']
        for parc in self:
            services = service_obj.search([('parc_installe_id', '=', parc.id)])  # permet de ne faire d'un seul search
            parc.service_count = len(services.filtered('recurrence'))
            parc.a_programmer_count = len(services.filtered(lambda s: not s.recurrence))

    @api.multi
    def action_view_service(self):
        self.ensure_one()
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_service').read()[0]
        action['domain'] = [('parc_installe_id', '=', self.id), ('recurrence', '=', True)]
        action['context'] = {
            'default_partner_id': self.client_id.id,
            'default_address_id': self.site_adresse_id.id,
            'default_recurrence': True,
            'default_date_next': fields.Date.today(),
            'default_parc_installe_id': self.id,
            'default_origin': u"[parc installé] " + (self.name or ''),
            'default_type_id': self.env.ref('of_service.of_service_type_maintenance').id,
        }
        return action

    @api.multi
    def action_view_a_programmer(self):
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
        action['domain'] = [('parc_installe_id', '=', self.id), ('recurrence', '=', False)]
        action['context'] = {
            'default_partner_id': self.client_id.id,
            'default_address_id': self.site_adresse_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_parc_installe_id': self.id,
            'default_origin': u"[parc installé] " + (self.name or ''),
            'default_type_id': self.env.ref('of_service_parc_installe.of_service_type_sav').id,
        }
        return action

    @api.multi
    def action_prevoir_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
        action['name'] = u"Prévoir une intervention"
        action['view_mode'] = "form"
        action['view_ids'] = False
        action['view_id'] = self.env['ir.model.data'].xmlid_to_res_id("of_service.view_of_service_form")
        action['views'] = False
        action['target'] = "new"
        action['context'] = {
            'default_partner_id': self.client_id.id,
            'default_address_id': self.site_adresse_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_parc_installe_id': self.id,
            'default_origin': u"[Parc installé] " + (self.name or ''),
            'default_type_id': self.env.ref('of_service_parc_installe.of_service_type_sav').id,
        }
        return action

    @api.multi
    def historique(self, intervention):
        """
        :param intervention: Intervention de départ
        :return: Renvoi les 3 interventions précédent celle envoyée en paramètre.
        """
        self.ensure_one()
        return self.env['of.planning.intervention'].search([
            ('id', 'in', self.intervention_ids.ids),
            ('date', '<', intervention.date)
            ], order="date DESC", limit=3)
