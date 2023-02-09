# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_logo_ids = fields.Many2many(
        comodel_name='of.company.multi.logos', relation='company_logo', column1='company_id', column2='logo_id',
        string=u"Logos")
    of_logo_footer = fields.Boolean(
        string=u"Logos en pied de page", compute='_compute_of_logo_footer', store=True,
        help=u"Cette société utilise des logos à positionner juste au dessus du pied de page")

    @api.depends('of_logo_ids', 'of_logo_ids.name')
    def _compute_of_logo_footer(self):
        for company in self:
            company.of_logo_footer = any(
                name.startswith(u"Logo_footer") for name in company.of_logo_ids.mapped('name'))

    @api.multi
    def _write(self, vals):
        res = super(ResCompany, self)._write(vals)
        if 'of_logo_footer' in vals:
            # Utiliser le format de papier spécial
            if vals['of_logo_footer']:
                paperformat = self.env.ref('of_company_multi_logos.paperformat_euro_of_logo_footer')
            # Utiliser le format de papier standard
            else:
                paperformat = self.env.ref('report.paperformat_euro')
            self.write({'paperformat_id': paperformat.id})
        return res

    def get_logo_footer(self):
        self.ensure_one()
        return self.of_logo_ids.filtered(lambda s: s.name.startswith(u"Logo_footer")).mapped('logo')

    @api.multi
    def getLogo(self, name):
        """get the logo from a given name"""
        for logos in self.of_logo_ids:
            if logos.name == name:
                return logos.logo
        return False


class OfCompanyMultiLogos(models.Model):
    _name = 'of.company.multi.logos'
    _description = u"Contient les logos secondaires des sociétés"

    @api.model
    def _get_company(self):
        return self.env.user.company_id

    company_ids = fields.Many2many(
        comodel_name='res.company', relation='company_logo', column1='logo_id', column2='company_id',
        string=u"Sociétés", required=True, default=lambda self: self._get_company())
    logo = fields.Binary(string=u"Logo", required=True)
    name = fields.Char(string=u"Libellé", required=True)
    color = fields.Integer(string=u"Index de couleur")
    description = fields.Text(string=u"Description", translate=True)
    display_docs = fields.Boolean(string=u"Affiché dans les documents", default=True)

    def getLogo(self):
        return self.logo
