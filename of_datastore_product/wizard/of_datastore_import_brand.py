# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ImportBrand(models.TransientModel):
    _name = 'of.datastore.import.brand'

    datastore_supplier_id = fields.Many2one('of.datastore.supplier', string='Connector')
    partner_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier', '=', True)])
    product_categ_id = fields.Many2one('product.category', string=u"Catégorie")
    line_ids = fields.One2many('of.datastore.import.brand.line', 'wizard_id')

    @api.multi
    def button_import_brands(self):
        self.ensure_one()
        brand_obj = self.env['of.product.brand']
        for line in self.line_ids:
            if line.state != 'do':
                continue
            brand_obj.create({
                'name': line.name,
                'prefix': line.prefix,
                'logo': line.logo,
                'partner_id': (line.partner_id or self.partner_id).id,
                'of_import_categ_id': (line.product_categ_id or self.product_categ_id).id,
                'datastore_supplier_id': self.datastore_supplier_id.id,
            })


class ImportBrandLine(models.TransientModel):
    _name = 'of.datastore.import.brand.line'

    wizard_id = fields.Many2one('of.datastore.import.brand')
    name = fields.Char(string='Name', required=True)
    prefix = fields.Char(string='Prefix', required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier', '=', True)])
    product_categ_id = fields.Many2one('product.category', string=u"Catégorie")
    logo = fields.Binary(string='Logo')
    note_maj = fields.Text(string=u"Notes de mise à jour")
    state = fields.Selection([('do', u'Inclus'), ('dont', u'Exclus'), ('done', 'Existe')])

    @api.multi
    def button_inverse(self):
        new_state = {
            'do': 'dont',
            'dont': 'do',
            'done': 'done',
        }
        for line in self:
            line.state = new_state[line.state]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.datastore.import.brand',
            'res_id': line.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
