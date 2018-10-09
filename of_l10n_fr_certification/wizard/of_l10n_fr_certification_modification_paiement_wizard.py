# -*- encoding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import UserError


class OFAccountPaymentWizard(models.TransientModel):
    _name = "of.account.payment.wizard"
    _description = u"Remboursement, annulation ou modification d'un paiement par extourne comptable"

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
        context = {
            'default_partner_id': payment.partner_id.id or False,
            'default_amount': payment.amount or False,
            'default_payment_date': fields.Date.context_today(payment),
            'default_communication': payment.communication or False,
            'default_partner_type': payment.partner_type
        }

        # On vérifie si le module of_account_payment_mode est installé (existence du champ of_payment_mode_id).
        # Si oui, on ajoute les valeurs des champs supplémentaires qu'il a ajouté.
        if getattr(payment, 'of_payment_mode_id', False):
            context['default_of_payment_mode_id'] = payment.of_payment_mode_id.id or False

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

        # Appel action nouveau paiement
        return {
            'name': _(name),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
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

                # Remboursement
                # Dans le cas d'un remboursement, Il n'y a aucun lettrage après.
                # On peut donc faire un remboursement d'un paiement déjà lettré.
                if self.type_modification_payment == 'refund':
                    return self.get_action_payment_form(payment, 'refund')

                # Si on arrive ici, c'est une annulation ou une modification.
                # On va lettrer ensuite les écritures, donc les écritures d'origine ne doivent pas l'être.
                # On teste si c'est le cas.

                # On vérifie si le module OF remise en banque (of_account_payment_bank_deposit) est installé (existence du champ of_deposit_id).
                # Si oui, on vérifie que le paiement n'est pas remis en banque.
                if getattr(payment, 'of_deposit_id', False) and self.type_modification_payment != 'refund':
                    raise UserError(_(u"Le paiement a été remis en banque. Vous ne pouvez pas modifier ou annuler un paiement remis en banque."))
                if payment.has_invoices:
                    raise UserError(_(u"Le paiement est lié à une facture (lettrage). Vous ne pouvez modifier ou annuler un paiement que s'il n'est pas lettré. Annulez auparavant le lien entre la facture et le paiement pour pouvoir modifier ce paiement."))
                # On vérifie s'il n'y a pas un autre lettrage.
                for move_line in payment.move_line_ids:
                    if move_line.reconciled:
                        raise UserError(_(u"Le paiement est lettré. Vous ne pouvez modifier ou annuler qu'un paiement qui n'est pas lettré."))

                # Annulation
                if self.type_modification_payment == 'cancel':
                    # Pour annuler le paiement, on crée une contrepartie comptable. 
                    for move in payment.move_line_ids.mapped('move_id'):
                        rev_move = move.create_reversals(post=True, reconcile=True)
                        rev_move.ref = form.description or move.name
                    payment.active = False
                    # L'annulation a été faite. On va à la liste des paiements clients ou fournisseurs (appel de l'action).
                    if payment.partner_type == 'supplier':
                        return self.env.ref('account.action_account_payments_payable').read()[0]
                    else:
                        return self.env.ref('account.action_account_payments').read()[0]

                # Modification
                if self.type_modification_payment == 'modify':
                    for move in payment.move_line_ids.mapped('move_id'):
                        rev_move = move.create_reversals(post=True, reconcile=True)
                        rev_move.ref = form.description or move.name
                    payment.active = False
                    return self.get_action_payment_form(payment, 'modify')
