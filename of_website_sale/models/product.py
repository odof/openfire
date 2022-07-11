# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    website_name = fields.Char(string=u"Dénomination site web")

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        if self.id < 0:
            raise UserError(u"Vous ne pouvez publier un article centralisé qui n'est pas importé, "
                            u"importez l'article avant de le publier sur le site internet")
        else:
            return super(ProductTemplate, self).website_publish_button()
