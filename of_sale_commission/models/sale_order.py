# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_commi_ids = fields.One2many('of.sale.commi', 'order_id', string="Commissions vendeurs")
    of_nb_commis = fields.Integer(compute='_compute_nb_commis', string="Nb. Commissions")

    @api.depends('of_commi_ids')
    def _compute_nb_commis(self):
        for order in self:
            order.of_nb_commis = len(order.of_commi_ids)

    @api.multi
    def of_sale_commi_acompte_requis(self):
        """
        Fonction qui détermine la nécessité d'avoir un acompte dans la commande pour générer une commission sur acompte.
        Par exemple, pour une commande faisant l'objet d'un financement, l'acompte n'est en général pas exigé.
        :todo: Permettre de rendre l'acompte non obligatoire pour la commission selon la commande / le profil.
        """
        self.ensure_one()
        return True

    @api.multi
    def of_verif_acomptes(self):
        order_paid = order_not_paid = self.browse([]).sudo()
        for order in self:
            if order.state != 'sale':
                continue
            if order.of_sale_commi_acompte_requis() \
                    and len(order.of_echeance_line_ids) > 1 \
                    and order.of_echeance_line_ids[0].amount > order.of_payment_amount:
                order_not_paid |= order
            else:
                order_paid |= order
        commi_to_pay = order_paid.mapped('of_commi_ids').filtered(lambda commi: commi.state == 'draft')
        commit_not_to_pay = order_not_paid.mapped('of_commi_ids').filtered(lambda commi: commi.state == 'to_pay')

        commi_to_pay.action_to_pay()
        commit_not_to_pay.write({'state': 'draft'})

    @api.multi
    def write(self, vals):
        # En cas de modification des lignes de commande ou de l'échéancier, recalcul des commissions
        result = super(SaleOrder, self).write(vals)
        orders = self.sudo()
        if 'order_line' in vals:
            # Recalcul du montant des commissions
            for commi in orders.mapped('of_commi_ids'):
                if commi.total_du < 0:
                    # Annulation de commission generee a la main
                    continue
                if commi.state not in ('paid', 'to_cancel', 'cancel'):
                    commi.update_commi()
            orders.of_verif_acomptes()
        if 'of_echeance_line_ids' in vals:
            # Recalcul du montant dû des commissions
            for commi in orders.mapped('of_commi_ids'):
                commi.total_du = commi.get_total_du()
            orders.of_verif_acomptes()
        if vals.get('state') == 'done':
            orders.filtered(lambda o: o.state == 'draft').action_to_pay()
        return result

    @api.multi
    def get_active_commis(self):
        result = self.env['of.sale.commi']
        for order in self:
            commis = order.of_commi_ids.filtered(lambda commi: commi.state != 'cancel')
            cancel_commis = commis.filtered('cancel_commi_id')
            result |= commis - cancel_commis - cancel_commis.mapped('cancel_commi_id')
        return result

    @api.multi
    def action_cancel(self):
        super(SaleOrder, self).action_cancel()
        self.sudo().of_commi_ids.filtered(lambda c: c.state in ('draft', 'to_pay')).write({'state': 'cancel'})
        self.sudo().get_active_commis().action_cancel()
        return True

    @api.multi
    def action_confirm(self):
        super(SaleOrder, self).action_confirm()

        commi_obj = self.env['of.sale.commi'].sudo()

        for order in self.sudo():
            commi_vendeur = False
            for commi in order.of_commi_ids:
                if commi.state == 'cancel':
                    commi.write({'state': 'draft'})
                    commi.update_commi()
                    if commi.user_id == order.user_id:
                        commi_vendeur = True

            if not commi_vendeur:
                if order.user_id.of_profcommi_id:
                    commi_data = {
                        'name': order.name,
                        'state': 'draft',
                        'user_id': order.user_id.id,
                        'type': 'acompte',
                        'order_id': order.id,
                    }
                    commi = commi_obj.create(commi_data)
                    commi.create_lines(order.order_line)

        self.of_verif_acomptes()
        return True

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        # Ajout de la valeur of_commi_ids pour désactiver la création automatique de commissions
        # à la création de la facture.
        invoice_vals['of_commi_ids'] = []
        return invoice_vals

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        commi_obj = self.env['of.sale.commi'].sudo()
        commi_line_obj = self.env['of.sale.commi.line'].sudo()
        invoice_ids = super(SaleOrder, self).action_invoice_create(grouped=grouped, final=final)

        invoices = invoice_ids and self.env['account.invoice'].browse(invoice_ids)
        for invoice in invoices:
            orders = invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
            commis = orders.sudo().get_active_commis().filtered(
                lambda c: not c.inv_commi_id or c.inv_commi_id.state == 'cancel')
            user_commis = {}
            for commi in commis:
                if commi.user_id in user_commis:
                    user_commis[commi.user_id] |= commi
                else:
                    user_commis[commi.user_id] = commi
            for user, commis in user_commis.iteritems():
                inv_commi = commi_obj.create({
                    'name': invoice.origin,
                    'state': 'draft',
                    'user_id': user.id,
                    'type': 'solde',
                    'invoice_id': invoice.id,
                    'order_commi_ids': [(6, 0, commis.ids)],
                })

                commi_lines_data = inv_commi.make_commi_invoice_lines_from_old(commis, invoice, user.of_profcommi_id)
                for commi_line_data in commi_lines_data:
                    commi_line_obj.create(commi_line_data)

                # Créera des lignes manquantes dans le cas des bons de commandes multiples et mettra à jour les totaux
                inv_commi.create_lines(invoice.invoice_line_ids, True)
        return invoice_ids

    @api.multi
    def unlink(self):
        self.sudo().mapped('of_commi_ids').unlink()
        return super(SaleOrder, self).unlink()

    @api.multi
    def action_view_commissions(self):
        action = self.env.ref('of_sale_commission.action_of_sale_commi_tree').read()[0]
        action['domain'] = ['|', ('order_id', 'in', self.ids), ('order_commi_ids.order_id', 'in', self.ids)]
        action['context'] = {
            'default_type': 'acompte',
            'default_order_id': len(self) == 1 and self.id,
        }
        return action
