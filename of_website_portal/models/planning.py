# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import UserError


class OFService(models.Model):
    _inherit = 'of.service'

    website_published = fields.Boolean(string=u"Publié sur le site internet", copy=False)

    @api.multi
    def button_valider(self):
        # laisser le système calculer l'état
        res = super(OFService, self).button_valider()
        maintenance = self.env.ref('of_service.of_service_type_maintenance', raise_if_not_found=False)
        if self.tache_id.website_published and maintenance and self.type_id.id == maintenance.id:
            self.website_publish_button()
        return res

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        if not self.tache_id.website_published:
            raise UserError(u"La tâche du contrat doit être publiée pour pouvoir publier le contrat !")
        return self.write({'website_published': not self.website_published})


class OFPlanningTache(models.Model):
    _inherit = 'of.planning.tache'

    website_published = fields.Boolean(string=u"Publié sur le site internet", copy=False)

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        if self.website_published:
            if self.env['of.service'].search([('tache_id', '=', self.id), ('website_published', '=', True)]):
                raise UserError(u"Vous ne pouvez pas dépublier cette tâche car des contrats associés sont publiés !")
        else:
            if not self.fiscal_position_id:
                raise UserError(u"Vous devez définir une position fiscale avant de pouvoir publier cette tâche !")
            if not self.product_id:
                raise UserError(u"Vous devez définir un article lié avant de pouvoir publier cette tâche !")
        return self.write({'website_published': not self.website_published})

    @api.multi
    def write(self, vals):
        if 'product_id' in vals and not vals['product_id']:
            if self.filtered(lambda t: t.website_published):
                raise UserError(u"Vous ne pouvez pas supprimer l'article d'une tâche publiée !")
        if 'fiscal_position_id' in vals and not vals['fiscal_position_id']:
            if self.filtered(lambda t: t.website_published):
                raise UserError(u"Vous ne pouvez pas supprimer la position fiscale d'une tâche publiée !")
        return super(OFPlanningTache, self).write(vals)


class OFPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    @api.multi
    def can_cancel_from_website(self):
        self.ensure_one()
        date_limit = fields.Date.to_string(fields.Date.from_string(fields.Date.today()) + relativedelta(days=7))
        return self.date_date > date_limit
