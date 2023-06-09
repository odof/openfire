# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, models, fields, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_eco_organism_id = fields.Many2one(comodel_name='of.eco.organism', string=u"Éco-organisme")
    of_eco_contribution_id = fields.Many2one(comodel_name='of.eco.contribution', string=u"Éco-contribution")
