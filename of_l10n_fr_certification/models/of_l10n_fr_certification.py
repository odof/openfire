# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
import time


class OfLogPaiement(models.Model):
    _name = "of.log.paiement"
    _description = u"Table historique modifications paiements"

    create_date = fields.Datetime(u'Date de modification', readonly=True)
    create_uid = fields.Integer(u'ID utilisateur', readonly=True)
    user_name = fields.Text(u'Nom utilisateur', readonly=True)
    payment_date = fields.Date(u'Date paiement', readonly=True)
    paiement_id = fields.Integer(u'ID paiement', readonly=True)
    partner_id = fields.Integer(u'ID client/fournisseur', readonly=True)
    partner_name = fields.Text(u'Nom client/fournisseur', readonly=True)
    payment_reference = fields.Text(u'Ref. paiement', readonly=True)
    payment_type = fields.Text(u'Type', readonly=True)
    amount = fields.Float(u'Montant', readonly=True)
    state = fields.Text(u'État', readonly=True)
    communication = fields.Text(u'Mémo', readonly=True)
    name = fields.Text(u'Nom', readonly=True)
    of_payment_mode_id = fields.Integer(u'ID mode de paiement', readonly=True)
    of_payment_mode_name = fields.Text(u'Nom mode de paiement', readonly=True)
    company_id = fields.Text(u'ID société', readonly=True)
    company_name = fields.Text(u'Nom société', readonly=True)

    _order = 'id DESC'

    @api.model
    def create(self, vals):
        # Empêcher une modification de la table of.log.paiement
        return False

    @api.multi
    def write(self, vals):
        # Empêcher une modification de la table of.log.paiement
        return False

    @api.multi
    def unlink(self):
        # Empêcher une modification de la table of.log.paiement
        return False

    @api.model
    def _peupler_log_paiements_existants(self):
        # Lors de la 1ère installation, peupler l'historique avec les paiements validés existants.

        # On vérifie si le module of_account_payment_mode est installé (existence du champ of_payment_mode_id).
        # Si oui, on inclus les valeurs des champs supplémentaires qu'il a ajouté.
        if 'of_payment_mode_id' in self.env['account.payment']._fields:
            module_of_account_payment_mode = True
        else:
            module_of_account_payment_mode = False

        # On récupère les paiements validés existants qui ne sont pas déjà dans l'historique.
        if module_of_account_payment_mode:
            self._cr.execute(
                u"SELECT account_payment.*, res_company.name AS company_name, p.name AS partner_name,\
                  of_account_payment_mode.name AS mode_name, u.name AS user_name\
                FROM account_payment\
                LEFT JOIN of_log_paiement ON account_payment.id = of_log_paiement.paiement_id\
                LEFT JOIN res_partner AS p ON account_payment.partner_id = p.id\
                LEFT JOIN res_users ON account_payment.write_uid = res_users.id\
                LEFT JOIN res_partner AS u ON res_users.partner_id = u.id\
                LEFT JOIN res_company ON account_payment.company_id = res_company.id\
                LEFT JOIN of_account_payment_mode ON account_payment.of_payment_mode_id = of_account_payment_mode.id\
                WHERE of_log_paiement.paiement_id IS NULL AND account_payment.state in ('posted', 'reconciled')\
                ORDER BY account_payment.id")
        else:
            self._cr.execute(
                u"SELECT account_payment.*, res_company.name AS company_name, p.name AS partner_name,\
                  u.name AS user_name\
                FROM account_payment\
                LEFT JOIN of_log_paiement ON account_payment.id = of_log_paiement.paiement_id\
                LEFT JOIN res_partner AS p ON account_payment.partner_id = p.id\
                LEFT JOIN res_users ON account_payment.write_uid = res_users.id\
                LEFT JOIN res_partner AS u ON res_users.partner_id = u.id\
                LEFT JOIN res_company ON account_payment.company_id = res_company.id\
                WHERE of_log_paiement.paiement_id IS NULL AND account_payment.state in ('posted', 'reconciled')\
                ORDER BY account_payment.id")

        # On peuple l'historique.
        if module_of_account_payment_mode:
            for paiement in self._cr.dictfetchall():
                self._cr.execute(
                    u"INSERT INTO of_log_paiement (create_uid, user_name, create_date, paiement_id,"
                    u" payment_date, partner_id, partner_name,"
                    u" payment_reference, payment_type, amount,"
                    u" state, name, communication,"
                    u" of_payment_mode_id, of_payment_mode_name, company_id,"
                    u" company_name) "
                    u"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (paiement['write_uid'], paiement['user_name'], paiement['write_date'], paiement['id'],
                     paiement['payment_date'] or '', paiement['partner_id'], paiement['partner_name'] or '',
                     paiement['payment_reference'] or '', paiement['payment_type'], paiement['amount'],
                     paiement['state'] or '', paiement['name'] or '', paiement['communication'] or '',
                     paiement['of_payment_mode_id'], paiement['mode_name'] or '', paiement['company_id'],
                     paiement['company_name'] or ''))
        else:
            for paiement in self._cr.dictfetchall():
                self._cr.execute(
                    u"INSERT INTO of_log_paiement (create_uid, user_name, create_date, paiement_id,"
                    u" payment_date, partner_id, partner_name,"
                    u" payment_reference, payment_type, amount,"
                    u" state, name, communication,"
                    u" of_payment_mode_id, of_payment_mode_name, company_id,"
                    u" company_name) "
                    u"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, Null, Null, %s, %s)",
                    (paiement['write_uid'], paiement['user_name'], paiement['write_date'], paiement['id'],
                     paiement['payment_date'] or '', paiement['partner_id'], paiement['partner_name'] or '',
                     paiement['payment_reference'] or '', paiement['payment_type'], paiement['amount'],
                     paiement['state'] or '', paiement['name'] or '', paiement['communication'] or '',
                     paiement['company_id'], paiement['company_name'] or ''))

        return True


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = 'account.payment'

    active = fields.Boolean(string="Active", default=True)

    of_payment_type_readonly = fields.Boolean(string=u"Type de paiement en lecture seule")

    @api.model
    def create(self, vals):
        # Après la création, on ne veut plus avoir le type de paiement en lecture seule dans le cadre d'un remboursement
        if vals.get('of_payment_type_readonly'):
            vals['of_payment_type_readonly'] = False
        return super(AccountPayment, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(AccountPayment, self).write(vals)
        # On ignore les (nombreux) appels à write avec vals vide et quand il s'agit uniquement
        # d'une modification du lettrage (vals avec une seule clé 'invoice_ids')
        if vals and not (len(vals) == 1 and 'invoice_ids' in vals):
            user_name = self.env.user.name or ''
            # On récupère les paiements qui ont été modifiés.
            paiements = self.env['account.payment'].browse(self._ids)

            # On teste si le module of_account_payment_mode est installé (existence du champ of_payment_mode_id).
            # Si oui, on inclus les valeurs des champs supplémentaires qu'il a ajouté.
            if 'of_payment_mode_id' in self._fields:
                module_of_account_payment_mode = True
            else:
                module_of_account_payment_mode = False

            # On les parcourt un par un.
            for paiement in paiements:
                # Si c'est seulement une modification du paiement pour inscrire le no d'une remise en banque,
                # on ne fait pas d'enregistrement dans l'historique.
                if 'of_deposit_id' in vals and len(vals) == 1:
                    continue
                # On récupère l'état du paiement lors de sa dernière modification.
                self._cr.execute(
                    u"SELECT state from of_log_paiement WHERE paiement_id = %s ORDER BY id DESC LIMIT 1",
                    (paiement.id, ))
                state_avant = self._cr.fetchone()
                if state_avant:
                    state_avant = state_avant[0]
                else:
                    state_avant = ''
                # On n'enregistre les traces de modification du paiement que si il passe de brouillon à validé
                # ou l'inverse (on ignore les modifications quand est en brouillon).
                if state_avant == 'posted' or paiement.state == 'posted':
                    if module_of_account_payment_mode:
                        self._cr.execute(
                            u"INSERT INTO of_log_paiement (create_uid, user_name, create_date, paiement_id, "
                            u"payment_date, partner_id, partner_name, payment_reference, payment_type, amount, state, "
                            u"name, communication, of_payment_mode_id, of_payment_mode_name, company_id, company_name) "
                            u"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (self._uid, user_name, time.strftime('%Y-%m-%d %H:%M:%S'), paiement.id,
                             paiement.payment_date, paiement.partner_id.id or None, paiement.partner_id.name or '',
                             paiement.payment_reference or '', paiement.payment_type or '', paiement.amount,
                             paiement.state or '', paiement.name or '', paiement.communication or '',
                             paiement.of_payment_mode_id.id, paiement.of_payment_mode_id.name or '',
                             paiement.company_id.id, paiement.company_id.name or ''))
                    else:
                        self._cr.execute(
                            u"INSERT INTO of_log_paiement (create_uid, user_name, create_date, paiement_id, "
                            u"payment_date, partner_id, partner_name, payment_reference, payment_type, amount, state, "
                            u"name, communication, of_payment_mode_id, of_payment_mode_name, company_id, company_name) "
                            u"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, Null, Null, %s, %s)",
                            (self._uid, user_name, time.strftime('%Y-%m-%d %H:%M:%S'), paiement.id,
                             paiement.payment_date, paiement.partner_id.id or None, paiement.partner_id.name or '',
                             paiement.payment_reference or '', paiement.payment_type or '', paiement.amount,
                             paiement.state or '', paiement.name or '', paiement.communication or '',
                             paiement.company_id.id, paiement.company_id.name or ''))
        return res

    @api.multi
    def unlink(self):
        raise UserError(_(u"Vous ne pouvez pas supprimer un paiement.\nVous pouvez seulement le laisser en brouillon."))

    # Il y a un onchange dans payment.type qui change de manière non voulue la valeur du type de partenaire
    # dans le formulaire du nouveau paiement.
    # Fonction qui résout ce problème.
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        res = super(AccountPayment, self)._onchange_payment_type()
        if 'of_default_partner_type' in self._context:
            self.partner_type = self._context['of_default_partner_type']
        return res


class Module(models.Model):
    _name = "ir.module.module"
    _inherit = "ir.module.module"

    @api.multi
    def write(self, vals):
        # Empêcher la désinstallation des modules de certification comptable.
        if self.search(
                [('name', 'in', ('l10n_fr_certification', 'of_l10n_fr_certification')), ('id', 'in', self._ids)]
        ) and vals.get('state') == 'to remove':
            raise UserError(_(
                u"Vous ne pouvez pas désinstaller les modules l10n_fr_certification et of_l10n_fr_certification."))
        return super(Module, self).write(vals)
