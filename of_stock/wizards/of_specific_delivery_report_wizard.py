# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFSpecificDeliveryReportWizard(models.TransientModel):
    _name = 'of.specific.delivery.report.wizard'
    _description = u"Assistant de rapport BL spécifique"

    @api.model
    def default_get(self, fields=None):
        result = super(OFSpecificDeliveryReportWizard, self).default_get(fields)
        if self._context.get('active_model') == 'stock.picking' and self._context.get('active_id'):
            picking = self.env['stock.picking'].browse(self._context.get('active_id'))
            result['picking_id'] = picking.id
            result['line_ids'] = [(0, 0, {'move_id': move.id,
                                          'product_id': move.product_id.id,
                                          'selected': True}) for move in picking.move_lines]
        return result

    picking_id = fields.Many2one(comodel_name='stock.picking', string=u"Bon de livraison")
    line_ids = fields.One2many(
        comodel_name='of.specific.delivery.report.wizard.line', inverse_name='wizard_id', string=u"Lignes à imprimer")

    @api.multi
    def print_specific_report(self):
        self.ensure_one()

        # Impression du BL spécifique
        return self.env['report'].get_action(self, 'of_stock.of_specific_delivery_report')

    @api.multi
    def button_select_all(self, select=True):
        self.ensure_one()
        self.line_ids.write({'selected': select})
        return {"type": "ir.actions.do_nothing"}

    @api.multi
    def button_unselect_all(self):
        return self.button_select_all(select=False)


class OFDeliveryDivisionWizardLine(models.TransientModel):
    _name = 'of.specific.delivery.report.wizard.line'
    _description = u"Ligne de l'assistant de rapport BL spécifique"

    wizard_id = fields.Many2one(comodel_name='of.specific.delivery.report.wizard', string=u"Rapport BL spécifique")
    move_id = fields.Many2one(comodel_name='stock.move', string=u"Ligne du BL")
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", readonly=True)
    selected = fields.Boolean(string=u"Sélectionné")
