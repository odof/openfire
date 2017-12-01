# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = "res.company"
    of_logo_ids = fields.Many2many('of.company.multi.logos', 'company_logo', 'company_id', 'logo_id', string='Logos')

    @api.multi
    def getLogo(self, name):
        """get the logo from a given name"""
        for logos in self.of_logo_ids:
            if logos.name == name:
                return logos.logo
        return False

class OfCompanyMultiLogos(models.Model):
    _name = "of.company.multi.logos"
    _description = u"Contient les logos secondaires des sociétés"

    @api.model
    def _get_company(self):
        return self.env.user.company_id

    company_ids = fields.Many2many('res.company', 'company_logo', 'logo_id', 'company_id',
        string=u'Sociétés', required=True, default=lambda self: self._get_company())
    logo = fields.Binary(string=u'Logo', required=True)
    name = fields.Char(string=u"Libellé", required=True)
    color = fields.Integer(string=u'Indexe couleur')
    description = fields.Text(string=u"Description",translate=True)
    display_docs = fields.Boolean(string=u"Affiché dans les documents", default=True)

    def getLogo(self):
        return self.logo
