# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfPlanningIntervention(models.Model):
    _name = 'of.planning.intervention'
    _inherit = ['of.planning.intervention', 'of.crm.stage.auto.update']

    @api.model
    def create(self, vals):
        rec = super(OfPlanningIntervention, self).create(vals).sudo()
        if rec.order_date_vt_need_update():
            rec.order_id.of_date_vt = rec.date_date
        return rec

    @api.multi
    def write(self, vals):
        res = super(OfPlanningIntervention, self).write(vals)
        # les RDVs viennent d'être passés en "réalisé" ou on vient de rattacher une commande
        if vals.get('state', '') == 'done' or vals.get('order_id'):
            for rec in self:
                if rec.order_date_vt_need_update():
                    rec.order_id.of_date_vt = rec.date_date
        return res

    @api.multi
    def order_date_vt_need_update(self):
        self.ensure_one()
        of_tache_categ_vt_id = self.env['ir.values'].get_default('of.intervention.settings', 'of_tache_categ_vt_id')
        # Si ce RDV est de catégorie "visite technique", qu'il est réalisé,
        # et que c'est le dernier en date de la commande et que cette commande n'a pas déjà de date de visite technique
        # -> mettre à jour la date de visite technique de la commande
        if self.tache_id.tache_categ_id.id == of_tache_categ_vt_id and self.state == 'done' and self.order_id \
                and not self.order_id.of_date_vt:
            interv_other_ids = self.order_id.intervention_ids.filtered(
                lambda i: i.tache_id.tache_categ_id.id == of_tache_categ_vt_id and i.id != self.id
                          and i.state == 'done').sorted('date')
            return not interv_other_ids or (interv_other_ids and interv_other_ids[-1].date < self.date)
        return False


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    of_tache_categ_vt_id = fields.Many2one(
        comodel_name='of.planning.tache.categ', string=u"(OF) Catégorie des visites techniques",
        help=u"Catégorie des tâches de visite technique")

    @api.multi
    def set_of_tache_categ_vt_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'of_tache_categ_vt_id', self.of_tache_categ_vt_id.id)
