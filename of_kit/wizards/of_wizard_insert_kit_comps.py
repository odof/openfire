# -*- coding: utf-8 -*-

from odoo import api, fields, models

class OfWizardInsertKitComps(models.TransientModel):
    _name = "of.wizard.insert.kit.comps"

    product_id = fields.Many2one('product.product', string="Kit")
    comp_ids = fields.One2many('of.wizard.insert.kit.comps.line', 'wizard_id', string="Composants")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        comp_line_obj = self.env['of.wizard.insert.kit.comps.line']
        comp_lines = comp_line_obj.browse()
        for line in self.product_id.kit_line_ids:
            vals = {
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'product_uom_id': line.product_uom_id.id,
                'wizard_id': self._origin.id,
            }
            comp_lines += comp_line_obj.create(vals)
        # La ligne suivante sert à afficher les lignes dans le wizard.
        # Il faut quand-même laisser 'wizard_id' dans vals pour que le lien soit persistant.
        self.comp_ids = comp_lines

    @api.multi
    def button_confirm_lines(self):
        sale_order_obj = self.env['sale.order']
        order_line_obj = self.env['sale.order.line']
        sale_order = sale_order_obj.browse(self._context.get('active_ids')[0])
        for line in self.comp_ids.filtered('is_selected'):
            vals = {
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom_id.id,
                'order_id': sale_order.id,
            }
            order_line_obj.create(vals)
        sale_order._compute_tax_id()

    @api.multi
    def button_select_all(self, select=True):
        self.comp_ids.write({'is_selected': select})
        return {"type": "ir.actions.do_nothing"}

    def button_unselect_all(self):
        return self.button_select_all(select=False)

class OfWizardInsertKitCompsLine(models.TransientModel):
    _name = "of.wizard.insert.kit.comps.line"

    product_id = fields.Many2one('product.product', string="Article", required=True)
    product_uom_qty = fields.Float(string=u"Qté", required=True)
    product_uom_id = fields.Many2one('product.uom', string='UoM', required=True, domain="[('category_id', '=', product_uom_categ_id)]")
    product_uom_categ_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    is_selected = fields.Boolean(string=u"Sélectionné", default=True)
    wizard_id = fields.Many2one('of.wizard.insert.kit.comps', string="Wizard")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id

    @api.multi
    def button_inverse_selected(self):
        """
        Bouton permettant de changer l'état de sélection de la ligne.
        Fonctionnalité désactivée pour le moment en raison des clignottements désagréables.
        """
        for line in self:
            line.is_selected = not line.is_selected
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'of.wizard.insert.kit.comps',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.wizard_id.id,
            'target': 'new',
            'context': self._context
        }
