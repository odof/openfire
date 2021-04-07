# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_company_type_id = fields.Many2one(comodel_name='of.res.company.type', string=u"Type")
    of_company_sector_id = fields.Many2one(comodel_name='of.res.company.sector', string=u"Secteur")
    of_company_sales_group_id = fields.Many2one(comodel_name='of.res.company.sales.group', string=u"Groupe Ventes")


class OFResCompanyType(models.Model):
    _name = 'of.res.company.type'
    _description = u"Type de société"
    _order = 'sequence, name'

    sequence = fields.Integer(string=u"Séquence")
    name = fields.Char(string=u"Nom")


class OFResCompanySector(models.Model):
    _name = 'of.res.company.sector'
    _description = u"Secteur de société"
    _order = 'sequence, name'

    sequence = fields.Integer(string=u"Séquence")
    name = fields.Char(string=u"Nom")


class OFResCompanySalesGroup(models.Model):
    _name = 'of.res.company.sales.group'
    _description = u"Goupe Ventes de société"
    _order = 'sequence, name'

    sequence = fields.Integer(string=u"Séquence")
    name = fields.Char(string=u"Nom")
