# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OfSaleOrderVerification(models.TransientModel):
    _inherit = 'of.sale.order.verification'

    type = fields.Selection(selection_add=[
        ('date_de_pose', u'Date de pose prévisionnelle')
        ], string="Type")
    date = fields.Date(string=u"Date de pose")

    @api.model
    def do_verification(self, order):
        action, interrupt = super(OfSaleOrderVerification, self).do_verification(order)
        if self.env['ir.values'].get_default('sale.config.settings', 'of_sale_order_installation_date_control'):
            context = self.env.context.copy()
            skipped_types = context.get('skipped_types', [])
            if not (action or interrupt) and 'date_de_pose' not in skipped_types and \
               not context.get('no_verif_date_de_pose', False) and not order.of_date_de_pose:
                skipped_types.append('date_de_pose')
                context.update({
                    'default_type': 'date_de_pose',
                    'default_message': False,
                    'default_order_id': order.id,
                    'skipped_types': skipped_types,
                })
                return self.action_return(context, self.need_interrupt(order))
        return action, interrupt

    @api.model
    def action_return(self, context, type, titre="Informations"):
        return {
            'type': 'ir.actions.act_window',
            'name': titre,
            'res_model': 'of.sale.order.verification',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': str(context),
        }, type

    @api.multi
    def validate_step(self):
        super(OfSaleOrderVerification, self).validate_step()
        if self.type == 'date_de_pose' and self.order_id:
            self.order_id.write({'of_date_de_pose': self.date})
            self.order_id.order_line.update_procurement_date_planned()
