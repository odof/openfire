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

    @api.model
    def get_company_type_filter_ids(self):
        u"""
        Cette fonction renvois les informations nécessaires à l'utilisation du bouton de filtrage par type de société.
        Ce bouton est présent dans le tableau de bord du module ks_dashboard_ninja.
        """
        company_types = self.env['of.res.company.type'].search([])
        filters = []
        for type in company_types:
            fil = {'id': type.id, 'name': type.name}
            # On ne précise pas le type courant car de base le filtre est en "Tous"
            filters.append(fil)
        return filters


class OFResCompanySector(models.Model):
    _name = 'of.res.company.sector'
    _description = u"Secteur de société"
    _order = 'sequence, name'

    sequence = fields.Integer(string=u"Séquence")
    name = fields.Char(string=u"Nom")

    @api.model
    def get_company_sector_filter_ids(self):
        u"""
        Cette fonction renvois les informations nécessaires à l'utilisation du bouton de filtrage par secteur société.
        Ce bouton est présent dans le tableau de bord du module ks_dashboard_ninja.
        """
        company_sectors = self.search([])
        filters = []
        for sector in company_sectors:
            fil = {'id': sector.id, 'name': sector.name}
            # On ne précise pas le secteur courant car de base le filtre est en "Tous"
            filters.append(fil)
        return filters


class OFResCompanySalesGroup(models.Model):
    _name = 'of.res.company.sales.group'
    _description = u"Goupe Ventes de société"
    _order = 'sequence, name'

    sequence = fields.Integer(string=u"Séquence")
    name = fields.Char(string=u"Nom")
