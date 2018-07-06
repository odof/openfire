# -*- encoding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class OFAccountPaymentWizard(models.TransientModel):
    _name = "of.account.payment.wizard"
    _description = u"Remboursement, annulation ou modification d'un paiement"

    @api.model
    def _get_description(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            payment = self.env['account.payment'].browse(active_id)
            default_description = payment.name
            return default_description
        return

    @api.model
    def _get_state(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            payment = self.env['account.payment'].browse(active_id)
            return payment.state
        return

    date_payment_mod = fields.Date(string='Date de modification', default=fields.Date.context_today, required=True)
    description = fields.Char(string='Motif', default=_get_description)
    state = fields.Char(string='state', default=_get_state, invisible="1", required=False)
    type_modification_payment = fields.Selection([('cancel', 'Annuler'),('modify', 'Modifier'),('refund', 'Rembourser')],
        default='cancel', string=u'Méthode', required=True, help=u"Choisissez le type de modification du paiement")

    @api.model
    def get_action_payment_form(self, payment, type_paiement):
        """Fenêtre pour saisir un nouveau paiement suite à demande de modification ou de remboursement d'un paiement"""
        # @param type: choix de type de formulaire demandé : 'refund' ou 'modif'

        # On récupère les valeurs du paiement à modifier/à rembourser pour les proposer par défaut dans le nouveau paiement.
        values = []
        # Les catégories de paiement (étiquettes)
        if payment.of_tag_ids:
            for tag_id in payment.of_tag_ids:
                values.append(tag_id.id)

        context = {
            'default_partner_id': payment.partner_id.id or False,
            'default_of_payment_mode_id': payment.of_payment_mode_id.id or False,
            'default_amount': payment.amount or False,
            'default_payment_date': fields.Date.context_today(payment), #payment.payment_date or False,
            'default_of_ref_reglement': payment.of_ref_reglement or False,
            'default_communication': payment.communication or False,
            'default_of_tag_ids': values or False,
            'default_payment_transaction_id': payment.payment_transaction_id.id or False,
            'default_partner_type': payment.partner_type
        }

        if type_paiement == 'refund':
            name = 'Remboursement de paiement'
            # Si c'est un paiement client (à rembourser), on sélectionne recevoir de l'argent" dans la fenêtre de paiment.
            # Si c'est un paiement fournisseur (à rembourser), on sélection "Règlement".
            if payment.partner_type == 'customer':
                context['default_payment_type'] = 'outbound'
            else:
                context['default_payment_type'] = 'inbound'
            context['of_default_partner_type'] = payment.partner_type or False # Permet d'outrepasser un onchange.
        else:
            name = 'Modification de paiement'
            context['default_payment_type'] = payment.payment_type

        return {
            'name': _(name),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_type': 'form',
            'view_mode': 'form',
            'target' : 'new',
            'view_id': False,
            'context': context,
        }

    @api.multi
    def payment_modification(self):
        payment_obj = self.env['account.payment']

        for form in self:
            for payment in payment_obj.browse(dict(self._context or {}).get('active_ids')):

                if payment.state in ['draft']:  # Si paiement déjà en brouillon, pas la peine de passer par une contrepartie comptable pour modifier le paiement.
                    raise UserError(_(u"Le paiement est en brouillon (non validé en comptabilité). Vous pouvez le modifier directement sans faire une extourne comptable."))
                if bool(payment.of_deposit_id) and self.type_modification_payment != 'refund':
                    raise UserError(_(u"Le paiement a été remis en banque. Vous ne pouvez pas modifier ou annuler un paiement remis en banque."))
                if payment.has_invoices:
                    raise UserError(_(u"Le paiement est lié à une facture (lettrage). Vous ne pouvez modifier/annuler/rembourser un paiement que s'il n'est pas lettré. Annulez auparavant le lien entre la facture et le paiement pour pouvoir modifier ce paiement."))

                # Remboursement
                if self.type_modification_payment == 'refund':
                    return self.get_action_payment_form(payment, 'refund')

                # Annulation
                if self.type_modification_payment == 'cancel':
                    # Pour annuler le paiement, on crée une contrepartie comptable. 
                    for move in payment.move_line_ids.mapped('move_id'):
                        rev_move = move.create_reversals()
                        rev_move.ref = form.description or move.name
                    # Et on met le paiement en brouillon.
                    payment.active = False
                    return self.env['of.popup.wizard'].popup_return(u"Le paiement a bien été annulé avec une extourne comptable.", u"Annulation paiement")

                # Modification
                if self.type_modification_payment == 'modify':
                    for move in payment.move_line_ids.mapped('move_id'):
                        rev_move = move.create_reversals()
                        rev_move.ref = form.description or move.name
                    payment.active = False
                    return self.get_action_payment_form(payment, 'modify')
