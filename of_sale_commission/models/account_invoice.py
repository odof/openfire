# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import itertools
from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    of_commi_ids = fields.One2many(
        comodel_name='of.sale.commi', inverse_name='invoice_id', string=u"Commissions vendeurs")
    of_nb_commis = fields.Integer(compute='_compute_nb_commis', string=u"Nb. Commissions")

    @api.depends('of_commi_ids')
    def _compute_nb_commis(self):
        for invoice in self:
            invoice.of_nb_commis = len(invoice.of_commi_ids)

    @api.multi
    def copy(self, default=None):
        default = default or {}
        # On force les commissions à False pour éviter que celle du vendeur ne se regénère automatiquement.
        default['of_commi_ids'] = False

        result = super(AccountInvoice, self).copy(default=default)
        if self.type not in ('out_invoice', 'out_refund'):
            return result

        commi_obj = self.env['of.sale.commi'].sudo()
        commi_line_obj = self.env['of.sale.commi.line']

        for commi_orig in self.sudo().of_commi_ids:
            if commi_orig.state in ('draft', 'to_pay', 'paid'):
                commi = commi_obj.create({
                    'name': result.reference,
                    'state': 'draft',
                    'user_id': commi_orig.user_id.id,
                    'type': commi_orig.type,
                    'invoice_id': result.id,
                })

                commi_lines_data = commi.make_commi_invoice_lines_from_old(
                    commi_orig, result, commi.user_id.of_profcommi_id, commi.type, False)
                for commi_line_data in commi_lines_data:
                    commi_line_obj.create(commi_line_data)

                # Ne va créer aucune ligne, mais mettra à jour les totaux
                commi.create_lines(result.invoice_line_ids)
        return result

    @api.model
    def create(self, vals):
        commi_obj = self.env['of.sale.commi'].sudo()
        commi_line_obj = self.env['of.sale.commi.line'].sudo()
        commis_to_refund = self._context.get('of_commis_to_refund') or []
        if commis_to_refund:
            self = self.with_context(of_commis_to_refund=False)
            commis = commi_obj.browse(vals.pop('of_commi_ids'))
            commis_to_refund &= commis
        invoice = super(AccountInvoice, self).create(vals)
        commi_obj = self.env['of.sale.commi'].sudo()
        if commis_to_refund:
            for commi_orig in commis_to_refund:
                # Duplication des commissions
                commi = commi_obj.create({
                    'name': invoice.reference,
                    'state': 'draft',
                    'user_id': commi_orig.user_id.id,
                    'type': commi_orig.type,
                    'invoice_id': invoice.id,
                    # Si la commission d'origine a été payée on ne lie pas la nouvelle au bon de commande
                    # car l'annulation a aussi pris en compte le montant commissionné sur acompte
                    # et il faut donc recommissionner la totalité
                    'order_commi_ids': commi_orig.state == 'cancel' and [(6, 0, commi_orig.order_commi_ids.ids)],
                })

                commi_lines_data = commi.make_commi_invoice_lines_from_old(
                    commi_orig, invoice, commi.user_id.of_profcommi_id, commi.type, False)
                for commi_line_data in commi_lines_data:
                    commi_line_obj.create(commi_line_data)

                # Ne va créer aucune ligne, mais mettra à jour les totaux
                commi.create_lines(invoice.invoice_line_ids)
        elif 'of_commi_ids' not in vals\
                and invoice.type in ('out_invoice', 'out_refund')\
                and invoice.user_id.of_profcommi_id:
            # Création de commission pour les factures nouvellement créées
            commi_data = {
                'name': invoice.origin or invoice.reference,
                'state': 'draft',
                'user_id': invoice.user_id.id,
                'type': invoice.type == 'out_invoice' and 'solde' or 'avoir',
                'invoice_id': invoice.id,
            }
            commi = commi_obj.create(commi_data)
            commi.create_lines(invoice.invoice_line_ids)
        return invoice

    @api.multi
    def write(self, vals):
        result = super(AccountInvoice, self).write(vals)
        if 'invoice_line_ids' not in vals:
            return result
        # Recalcul des acomptes pour les lignes de facture modifiées
        recalc_filtre = [
            inv_val[1]
            for inv_val in vals.get('invoice_line_ids', [])
            if inv_val[0] == 1 and 'product_id' in inv_val[2]
        ]
        self.sudo().mapped('of_commi_ids').update_commi(recalc_filtre)
        return result

    @api.multi
    def action_invoice_paid(self):
        res = super(AccountInvoice, self).action_invoice_paid()
        draft_commis = self.sudo().mapped('of_commi_ids').filtered(lambda commi: commi.state == 'draft')
        draft_commis.action_to_pay()
        return res

    @api.multi
    def action_cancel(self):
        res = super(AccountInvoice, self).action_cancel()
        for invoice in self:
            for commi in invoice.of_commi_ids:
                if commi.state == 'draft' or (invoice.type == 'out_refund' and commi.state == 'to_pay'):
                    commi.write({'state': 'cancel'})
                elif commi.state != 'cancel':
                    raise UserError(
                        u"Vous annulez une facture qui a ete payée, ou alors la commission associée est corrompue !\n"
                        u"Commission : %i, beneficiaire : %s" % (commi.id, commi.user_id.name))
        return res

    def action_invoice_draft(self):
        res = super(AccountInvoice, self).action_invoice_draft()
        self.mapped('of_commi_ids').write({'state': 'draft'})
        return res

    @api.multi
    @api.depends('move_id.line_ids.amount_residual')
    def _compute_payments(self):
        # Ces lignes doivent être placées AVANT l'appel au super(), car cette opération peut invalider les
        # valeurs mises en cache par _compute_payments()
        partner_ids = self.mapped('partner_id').ids
        self.env['sale.order']\
            .search(['|', ('partner_id', 'in', partner_ids), ('partner_invoice_id', 'in', partner_ids)])\
            .of_verif_acomptes()
        super(AccountInvoice, self)._compute_payments()

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        result = super(AccountInvoice, self)._prepare_refund(
            invoice, date_invoice=date_invoice, date=date, description=description, journal_id=journal_id)
        # Un avoir ne doit pas générer automatiquement de commission.
        # Elles seront créées par copie de celles de la facture d'origine
        result['of_commi_ids'] = False
        return result

    @api.multi
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None):
        self = self.with_context(of_commis_to_refund=False)
        refunds = super(AccountInvoice, self).refund(
            date_invoice=date_invoice, date=date, description=description, journal_id=journal_id)
        commi_obj = self.env['of.sale.commi']
        commi_line_obj = self.env['of.sale.commi.line']

        refund_mode = self._context.get('of_refund_mode')
        for invoice, refund in itertools.izip(self, refunds):
            if refund.type == 'out_refund':
                commi_type = 'avoir'
            elif refund.type == 'out_invoice':
                commi_type = 'solde'
            else:
                continue

            for commi_inv in invoice.of_commi_ids:
                if commi_inv.state in ('draft', 'to_pay') and refund_mode in ('cancel', 'modify'):
                    commi_inv.state = 'cancel'
                    # S'il y a des commandes annulées avec des commissions d'acompte liées à cette commission de solde
                    # alors on annule les commissions d'acompte non payées et on crée des commissions inverses pour
                    # annuler les paiements des commissions d'acompte déjà payées
                    order_commis_to_cancel = commi_inv.order_commi_ids.filtered(
                        lambda c: c.state != 'cancel' and c.order_id.state == 'cancel').sudo()
                    # commissions d'acompte non payées
                    commis_to_cancel = order_commis_to_cancel.filtered(lambda c: c.state in ('draft', 'to_pay'))
                    commis_to_cancel and commis_to_cancel.write({'state': 'cancel'})
                    # commissions d'acompte déjà payées
                    commis_already_paid = order_commis_to_cancel.filtered(lambda c: c.state == 'paid')
                    commis_already_paid and commis_already_paid.action_cancel()
                elif commi_inv.state in ('draft', 'to_pay', 'paid'):
                    # Création d'une commission inverse
                    commi_data = {
                        'name': invoice.reference,
                        'state': 'draft',
                        'user_id': commi_inv.user_id.id,
                        'type': commi_type,
                        'invoice_id': refund.id,
                    }
                    commi = commi_obj.create(commi_data)

                    commi_lines_data = commi.make_commi_invoice_lines_from_old(
                        commi_inv, refund, commi_inv.user_id.of_profcommi_id, commi_type, True)
                    for commi_line_data in commi_lines_data:
                        commi_line_obj.create(commi_line_data)
                    commi.total_du = commi.get_total_du()
        return refunds

    @api.multi
    def unlink(self):
        # Appel manuel de unlink() pour vérifier que les commissions autorisent leur suppression
        self.mapped('of_commi_ids').unlink()
        return super(AccountInvoice, self).unlink()

    @api.multi
    def action_view_commissions(self):
        action = self.env.ref('of_sale_commission.action_of_sale_commi_tree').read()[0]
        action['domain'] = [
            '|', '|',
            ('invoice_id', 'in', self.ids),
            ('inv_commi_id.invoice_id', 'in', self.ids),
            ('cancel_commi_id.inv_commi_id.invoice_id', 'in', self.ids)]
        commi_type = 'solde' if self.type == 'out_invoice' else 'avoir'
        action['context'] = {
            'default_type': commi_type,
            'default_invoice_id': len(self) == 1 and self.id,
        }
        return action

    @api.model
    def _get_refund_modify_read_fields(self):
        # Récupération des commissions de la facture d'origine lors d'un avoir de modification
        return super(AccountInvoice, self)._get_refund_modify_read_fields() + ['of_commi_ids']
