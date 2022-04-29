# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFPlanningIntervention(models.Model):
    _name = 'of.planning.intervention'
    _inherit = ['of.planning.intervention', 'of.crm.stage.auto.update']

    @api.onchange('address_id')
    def _onchange_address_id_warning(self):
        if not self.address_id:
            return
        warning = {}
        partner = self.address_id

        # If partner has no warning, check its parents
        # invoice_warn is shared between different objects
        while not partner.of_is_planning_warn and partner.parent_id:
            partner = partner.parent_id

        if partner.of_is_planning_warn and partner.invoice_warn != 'no-message':
            # Block if partner only has warning but parent company is blocked
            if partner.invoice_warn != 'block' and partner.parent_id and partner.parent_id.invoice_warn == 'block':
                partner = partner.parent_id
            title = u"Warning for %s" % partner.name
            message = partner.invoice_warn_msg
            warning = {
                    'title': title,
                    'message': message,
            }
            if partner.invoice_warn == 'block':
                self.update({'partner_id': False, 'address_id': False,})
                return {'warning': warning}

        if warning:
            return {'warning': warning}

    @api.model
    def create(self, vals):
        rec = super(OFPlanningIntervention, self).create(vals).sudo()
        if rec.order_date_vt_need_update():
            rec.order_id.of_date_vt = rec.date_date
        return rec

    @api.multi
    def write(self, vals):
        res = super(OFPlanningIntervention, self).write(vals)
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

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        # Si la commande a une durée de pose prévisionnelle, inhiber les mises à jour de durée automatiques
        if self.order_id and self.order_id.of_duration:
            self = self.with_context(of_inhiber_maj_duree=True)
        super(OFPlanningIntervention, self)._onchange_tache_id()

    @api.onchange('order_id')
    def onchange_order_id(self):
        # Si la commande a une durée de pose prévisionnelle, inhiber les mises à jour de durée automatiques
        if self.order_id and self.order_id.of_duration:
            self.duree = self.order_id.of_duration
            self = self.with_context(of_inhiber_maj_duree=True)
        return super(OFPlanningIntervention, self).onchange_order_id()


class OFInterventionSettings(models.TransientModel):
    _inherit = 'of.intervention.settings'

    of_tache_categ_vt_id = fields.Many2one(
        comodel_name='of.planning.tache.categ', string=u"(OF) Catégorie des visites techniques",
        help=u"Catégorie des tâches de visite technique")

    @api.multi
    def set_of_tache_categ_vt_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'of.intervention.settings', 'of_tache_categ_vt_id', self.of_tache_categ_vt_id.id)
