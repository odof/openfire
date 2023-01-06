# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    of_pricelist_id = fields.Many2one(comodel_name='product.pricelist', string=u"Liste de prix par défaut")
    of_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string=u"Position fiscale par défaut")
    of_tab_ids = fields.Many2many(
        comodel_name='of.tab', relation='res_users_of_tab_rel', column1='user_id', column2='tab_id', string="Onglets")


class OFTab(models.Model):
    _name = 'of.tab'
    _description = 'Onglet'
    _order = 'name asc'

    name = fields.Char(string="Nom", required=True)
    code = fields.Char(string="Code", required=True)
