# -*- coding: utf-8 -*-

from odoo import api, models, fields


class OFProductBrand(models.Model):
    _inherit = 'of.product.brand'

    of_website_planning_published = fields.Boolean(
        string=u"Publié prise de RDV en ligne", copy=False, oldname='website_published')

    @api.multi
    def button_of_website_planning_published(self):
        self.ensure_one()
        return self.write({'of_website_planning_published': not self.of_website_planning_published})


class ProductCategory(models.Model):
    _inherit = 'product.category'

    of_website_planning_published = fields.Boolean(
        string=u"Publié prise de RDV en ligne", copy=False, oldname='website_published')

    @api.multi
    def button_of_website_planning_published(self):
        self.ensure_one()
        return self.write({'of_website_planning_published': not self.of_website_planning_published})
