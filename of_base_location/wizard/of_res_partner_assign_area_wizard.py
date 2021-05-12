# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFResPartnerAssignAreaWizard(models.TransientModel):
    _name = 'of.res.partner.assign.area.wizard'
    _description = u"Assistant permettant l'affectation des secteurs aux partenaires"

    @api.model
    def default_get(self, fields):
        result = super(OFResPartnerAssignAreaWizard, self).default_get(fields)
        if self._context.get('active_model') == 'res.partner' and self._context.get('active_ids'):
            result['partner_ids'] = [(6, 0, self._context.get('active_ids'))]
        return result

    partner_ids = fields.Many2many(comodel_name='res.partner', string=u"Partenaires à mettre à jour")
    area_id = fields.Many2one(comodel_name='of.secteur', string=u"Secteur", required=True)
    area_type = fields.Selection(
        selection=[('tech', u"Technique"),
                   ('com', u"Commercial"),
                   ('tech_com', u"Technique & Commercial")], string=u"Type de secteur", required=True)

    @api.multi
    def action_update(self):
        self.ensure_one()
        if self.area_type == 'tech':
            self.partner_ids.write({'of_secteur_tech_id': self.area_id.id})
        elif self.area_type == 'com':
            self.partner_ids.write({'of_secteur_com_id': self.area_id.id})
        elif self.area_type == 'tech_com':
            self.partner_ids.write({'of_secteur_tech_id': self.area_id.id, 'of_secteur_com_id': self.area_id.id})
        return True
