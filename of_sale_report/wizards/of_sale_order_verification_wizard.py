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
        action, type = super(OfSaleOrderVerification, self).do_verification(order)
        skipped_types = self._context.get('skipped_types', [])
        if not (action or type) and 'date_de_pose' not in skipped_types and \
                not self._context.get('no_date_de_pose', False):
            if not order.of_date_de_pose:
                skipped_types.append('date_de_pose')
                context = {
                    'default_type': 'date_de_pose',
                    'default_message': False,
                    'default_order_id': order.id,
                    'skipped_types' : skipped_types,
                }
                return self.action_return(context, 'date_de_pose')
        return action, type

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
    def next_step(self):
        action = super(OfSaleOrderVerification, self).next_step()
        if self.type == 'date_de_pose':
            self.order_id.write({'of_date_de_pose': self.date})
        return action
