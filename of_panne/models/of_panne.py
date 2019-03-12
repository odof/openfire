# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OfPanne(models.Model):
    _name = "of.panne"

    name = fields.Char(string="Nom", required=True)
    partner_id = fields.Many2one('res.partner', string="Client", required=True)
    parc_installe_id = fields.Many2one('of.parc.installe', string=u"Parc installé", required=True)
    tache_id = fields.Many2one('of.planning.tache', string=u"Tâche", required=True)
    intervention_model_id = fields.Many2one('of.planning.intervention.model', string=u"Modèle d'intervention")
    equipe_id = fields.Many2one('of.planning.equipe', string=u"Équipe")
    notes = fields.Text(string="Notes")
    notes_client = fields.Text(related='partner_id.comment', string="Notes client", readonly=True)
    state = fields.Selection([('todo', u'À prendre en charge'), ('doing', 'Prise en charge'), ('done', u'Terminée')], string=u"État", default="todo", required=True)

    @api.onchange('parc_installe_id')
    def onchange_parc_installe(self):
        self.partner_id = self.parc_installe_id.site_adresse_id or self.parc_installe_id.client_id

    @api.onchange('intervention_model_id')
    def onchange_intervention_model(self):
        self.tache_id = self.intervention_model_id.tache_id

