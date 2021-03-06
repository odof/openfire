# -*- coding: utf-8 -*-

from odoo import models, api, fields


class RgpdRequiredFields(models.AbstractModel):
    _name = 'of.rgpd.required.fields'

    of_accord_communication = fields.Boolean(string=u"Autorise recevoir communication")
    of_date_accord_communication = fields.Date(string=u"Date de l'autorisation")
    of_preuve_accord_communication = fields.Text(string=u"Preuve autorisation")


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'of.rgpd.required.fields']

    # Champs pour autorisation recevoir communication (exigence RGPD)

    # On redéfinit le champ opt_out pour le mettre en champ calculé (inverse de of_accord_communication).
    opt_out = fields.Boolean(
        'Opt-out', compute='_compute_opt_out',
        help="If opt-out is checked, this contact has refused to receive emails for mass mailing and marketing "
             "campaign. Filter 'Available for Mass Mailing' allows users to filter the partners when performing "
             "mass mailing.", store=True)

    @api.multi
    @api.depends('of_accord_communication')
    def _compute_opt_out(self):
        for partner in self:
            partner.opt_out = not partner.of_accord_communication
