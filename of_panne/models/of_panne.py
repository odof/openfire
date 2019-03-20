# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfPanne(models.Model):
    _name = "of.panne"

    name = fields.Char(string="Nom", required=True)
    active = fields.Boolean(strin="Actif", default=True)
    partner_id = fields.Many2one('res.partner', string="Client", required=True)
    parc_installe_id = fields.Many2one('of.parc.installe', string=u"Parc installé", required=True)
    tache_id = fields.Many2one('of.planning.tache', string=u"Tâche", required=True)
    intervention_model_id = fields.Many2one('of.planning.intervention.model', string=u"Modèle d'intervention")
    intervention_id = fields.Many2one('of.planning.intervention', string="Intervention", copy=False)
    equipe_id = fields.Many2one('of.planning.equipe', string=u"Équipe", copy=False)
    notes = fields.Text(string="Notes")
    notes_client = fields.Text(related='partner_id.comment', string="Notes client", readonly=True)
    state = fields.Selection([('todo', u'À prendre en charge'), ('doing', 'Prise en charge'), ('done', u'Terminée')], string=u"État", compute="_compute_state", store=True)
    panne_ids = fields.One2many('of.panne', related="parc_installe_id.panne_ids", string="Historique")

    @api.depends('intervention_id', 'intervention_id.state')
    def _compute_state(self):
        for panne in self:
            if not panne.intervention_id:
                panne.state = 'todo'
            elif panne.intervention_id.state in ['done', 'cancel']:
                panne.state = 'done'
            else:
                panne.state = 'doing'

    @api.onchange('parc_installe_id')
    def onchange_parc_installe(self):
        self.partner_id = self.parc_installe_id.site_adresse_id or self.parc_installe_id.client_id

    @api.onchange('intervention_model_id')
    def onchange_intervention_model(self):
        self.tache_id = self.intervention_model_id.tache_id

    def toggle_active(self):
        self.active = not self.active

    def action_view_interventions(self):
        if not self.intervention_id:
            return
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]
        action['domain'] = [('id', '=', self.intervention_id.id)]
        return action

class OfPlanningIntervention(models.Model):
    _inherit = "of.planning.intervention"

    panne_id = fields.Many2one('of.panne', string=u"Panne liée")

class OfParcInstalle(models.Model):
    _inherit = "of.parc.installe"

    panne_ids = fields.One2many('of.panne', 'parc_installe_id', string="Pannes")
