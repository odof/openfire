# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ImportBrand(models.TransientModel):
    _name = 'of.datastore.import.brand'

#     def _default_line_ids(self):
#         supplier_id = self._context['active_id']
#         supplier = self.env['of.datastore.supplier'].browse(supplier_id)
#         client = supplier.of_datastore_connect()[supplier.id]
#         if isinstance(client, basestring):
#             raise UserError(u'Échec de la connexion à la base centrale')
#         ds_brand_obj = supplier.of_datastore_get_model(client, 'of.product.brand')
#         ds_brand_ids = supplier.of_datastore_search(ds_brand_obj, [])
#         ds_brand_data = supplier.of_datastore_read(ds_brand_obj, ds_brand_ids, ['name', 'prefix', 'logo'])
#         brand_names = self.env['of.product.brand'].search([]).mapped('name')
#         return [{
#             'datastore_supplier_id': supplier_id,
#             'name': ds_brand['name'],
#             'prefix': ds_brand['prefix'],
#             'logo': ds_brand['logo'],
#             'state': 'done' if ds_brand['name'] in brand_names else 'do',
#             } for ds_brand in ds_brand_data]

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
                'datastore_supplier_id': self._context['active_id'],
            })

# "type": "ir.actions.do_nothing"

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
            'type': 'ir.actions.client',
            'tag': '',
        }
