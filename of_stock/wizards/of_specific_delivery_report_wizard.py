# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OFSpecificDeliveryReportWizard(models.TransientModel):
    _name = 'of.specific.delivery.report.wizard'
    _inherit = 'mail.thread'
    _description = u"Assistant de rapport Transfert spécifique"

    def pdf_mention_legale(self):
        return self.env['ir.values'].get_default('stock.config.settings', 'pdf_mention_legale') or ""

    @api.model
    def default_get(self, fields=None):
        result = super(OFSpecificDeliveryReportWizard, self).default_get(fields)
        if self._context.get('active_model') == 'stock.picking' and self._context.get('active_id'):
            picking = self.env['stock.picking'].browse(self._context.get('active_id'))
            result['picking_id'] = picking.id
            result['of_transporter_id'] = picking.of_transporter_id and picking.of_transporter_id.id or False
            result['line_ids'] = [(0, 0, {'move_id': move.id,
                                          'product_id': move.product_id.id,
                                          'selected': True}) for move in picking.move_lines]
        return result

    picking_id = fields.Many2one(comodel_name='stock.picking', string=u"Bon de livraison")
    picking_type_code = fields.Selection(related='picking_id.picking_type_code', readonly=True)
    of_transporter_id = fields.Many2one(comodel_name='res.partner', string=u"Transporteur")
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

    @api.multi
    def action_picking_send(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'of.specific.delivery.report.wizard',
            'default_res_id': self.ids[0],
            'default_partner_ids': [(6, 0, self.of_transporter_id and [self.of_transporter_id.id] or [])],
            'default_template_id': self.env.ref('of_stock.of_stock_specific_delivery_email_template').id,
            'default_composition_mode': 'comment',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


class OFDeliveryDivisionWizardLine(models.TransientModel):
    _name = 'of.specific.delivery.report.wizard.line'
    _description = u"Ligne de l'assistant de rapport BL spécifique"

    wizard_id = fields.Many2one(comodel_name='of.specific.delivery.report.wizard', string=u"Rapport BL spécifique")
    move_id = fields.Many2one(comodel_name='stock.move', string=u"Ligne du BL")
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article", readonly=True)
    selected = fields.Boolean(string=u"Sélectionné")
