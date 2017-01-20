# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = "res.company"
    of_logo_ids = fields.One2many('of.company.multi.logos', 'company_id', string='Logos')

    @api.multi
    def getLogo(self, name):
        """get the logo from a given name"""
        for logos in self.of_logo_ids:
            if logos.name == name:
                return logos.logo
        return False

class OfCompanyMultiLogos(models.Model):
    _name = "of.company.multi.logos"
    _description = "contains the secondary logos of a company"

    company_id = fields.Many2one('res.company', string=_('Company'), required=True)
    logo = fields.Binary(string='Logo', required=True)
    name = fields.Char(string=_('Name'), required=True)

    def getLogo(self):
        return self.logo
