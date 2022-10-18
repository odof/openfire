# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFSaleOrderClosureWizard(models.TransientModel):
    _name = 'of.sale.order.closure.wizard'
    _description = u"Assistant de clôture des commandes de vente"

    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande à clôturer")
    info_txt = fields.Text(string=u"Texte d'information")

    @api.model
    def default_get(self, fields):
        result = super(OFSaleOrderClosureWizard, self).default_get(fields)
        if self._context.get('active_model') == 'sale.order' and self._context.get('active_id'):
            order = self.env['sale.order'].browse(self._context.get('active_id'))
            result['order_id'] = order.id

            info_txt = ""

            if order.invoice_status != 'invoiced':
                info_txt += u"- La commande n'est pas entièrement facturée\n"

            invoices = order.invoice_ids.filtered(lambda inv: inv.state not in ('paid', 'cancel'))
            if invoices:
                info_txt += u"- La commande a des factures en attente : " +\
                            ', '.join(invoices.mapped(lambda rec: rec.number or u"Facture brouillon")) + "\n"

            pickings = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            if pickings:
                info_txt += u"- La commande a des BL en attente : " + ', '.join(pickings.mapped('name')) + "\n"

            purchases = order.purchase_ids.filtered(lambda p: p.state not in ('purchase', 'done', 'cancel'))
            if purchases:
                info_txt += u"- La commande a des achats en attente : " + ', '.join(purchases.mapped('name')) + "\n"

            interventions = order.intervention_ids.filtered(lambda inter: inter.state not in ('done', 'cancel'))
            if interventions:
                info_txt += u"- La commande a des RDV d'intervention en attente : " +\
                            ', '.join(interventions.mapped('name')) + "\n"

            if info_txt:
                info_txt = u"Attention, certaines actions sont encore nécessaires :\n" + info_txt

            info_txt += u"\nÊtes-vous sûr de vouloir clôturer cette commande ?"
            result['info_txt'] = info_txt

        return result

    @api.multi
    def action_close(self):
        self.ensure_one()
        self.order_id.state = 'closed'
        return True
