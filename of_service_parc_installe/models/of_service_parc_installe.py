# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class OfService(models.Model):
    _inherit = "of.service"

    parc_installe_id = fields.Many2one(
        'of.parc.installe', string=u"No de série",
        domain="partner_id and [('client_id', '=', partner_id), '|', ('site_adresse_id', '=', False), "
               "('site_adresse_id', '=', address_id)] or address_id and [('client_id', 'parent_of', address_id), '|', "
               "('site_adresse_id', '=', False), ('site_adresse_id', '=', address_id)] or []")
    parc_installe_product_id = fields.Many2one(
        'product.product', string=u"Désignation", related="parc_installe_id.product_id", readonly=True)
    parc_installe_site_adresse_id = fields.Many2one(
        'res.partner', string=u"Adresse de pose", related="parc_installe_id.site_adresse_id", readonly=True)
    parc_installe_note = fields.Text(string=u"Note", related="parc_installe_id.note", readonly=True)
    sav_id = fields.Many2one(
        "project.issue", string="SAV", domain="['|', ('partner_id', '=', partner_id), ('partner_id', '=', address_id)]")

    @api.onchange('address_id')
    def _onchange_address_id(self):
        self.ensure_one()
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


class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    parc_installe_id = fields.Many2one(
        'of.parc.installe', string=u"Parc installé",
        domain="['|', '|', ('client_id', '=', partner_id), ('client_id', '=', address_id), "
               "('site_adresse_id', '=', address_id)]")
    parc_installe_product_name = fields.Char(
        string=u"Désignation", related="parc_installe_id.product_id.name", readonly=True)

    @api.model
    def create(self, vals):
        service_obj = self.env['of.service']
        parc_obj = self.env['of.parc.installe']
        service = vals.get('service_id') and service_obj.browse(vals['service_id'])
        parc = False
        if service:
            parc = service.parc_installe_id
            vals['parc_installe_id'] = parc and parc.id
        parc = not parc and vals.get('parc_installe_id') and parc_obj.browse(vals['parc_installe_id'])
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

class ProjectIssue(models.Model):
    _inherit = 'project.issue'

    of_a_programmer_count = fields.Integer(compute="_compute_of_a_programmer_count")

    @api.multi
    def _compute_of_a_programmer_count(self):
        """Smart button vue SAV : renvoi le nombre d'interventions à programmer liées à la machine installée"""
        service_obj = self.env['of.service']
        for sav in self:
            sav.of_a_programmer_count = len(service_obj.search([('sav_id', '=', sav.id), ('recurrence', '=', False)]))

    @api.multi
    def action_view_a_programmer(self):
        self.ensure_one()
        action = self.env.ref('of_service_parc_installe.of_service_parc_installe_open_a_programmer').read()[0]
        action['domain'] = [('sav_id', '=', self.id), ('recurrence', '=', False)]
        action['context'] = {
            'default_partner_id': self.of_parc_installe_client_id.id,
            'default_address_id': self.of_parc_installe_lieu_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_sav_id': self.id,
            'default_parc_installe_id': self.of_produit_installe_id.id,
            'default_origin': u"[SAV] " + self.name,
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
            'default_partner_id': self.of_parc_installe_client_id.id,
            'default_address_id': self.of_parc_installe_lieu_id.id,
            'default_recurrence': False,
            'default_date_next': fields.Date.today(),
            'default_sav_id': self.id,
            'default_parc_installe_id': self.of_produit_installe_id.id,
            'default_origin': u"[SAV] " + self.name,
        }
        return action
