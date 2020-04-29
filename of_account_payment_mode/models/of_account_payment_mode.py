# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import traceback

from odoo.addons.mail.models.mail_template import format_date

class OfAccountPaymentMode(models.Model):
    _name = 'of.account.payment.mode'
    _description = 'Payment mode'
    _order = "sequence"

    name = fields.Char('Name', required=True, help='Mode of Payment')
    journal_id = fields.Many2one('account.journal', 'Journal', domain=[('type', 'in', ('bank', 'cash'))],
                                 required=True, help='Bank or Cash Journal for the Payment Mode')
    company_id = fields.Many2one('res.company', 'Company', required=True)
    partner_id = fields.Many2one(related='company_id.partner_id', string='Partner', store=True)
    journal_type = fields.Selection(related='journal_id.type', string='Type', readonly=True)

    active = fields.Boolean(string="Actif", default=True)
    config_affichage = fields.Text(string='Configuration', help=u'Attention niveau avancé!\n Décrivez par texte et balises mako (${variable}) ce qui sera affiché sur la facture.')
    sequence = fields.Integer(default=100, string=u"Séquence")

    _sql_constraints = [('name_uniq', 'unique (name)', u"Ce mode de paiement existe déjà !")]

    @api.model_cr_context
    def _auto_init(self):
        '''
        Create one payment mode by cash/bank journal
        '''
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.tables WHERE table_name = '%s'" % (self._table,))
        exists = bool(cr.fetchall())
        res = super(OfAccountPaymentMode, self)._auto_init()
        if not exists:
            cr.execute("INSERT INTO %s (name, journal_id, company_id, partner_id)\n"
                       "SELECT j.name, j.id, j.company_id, c.partner_id\n"
                       "FROM account_journal AS j\n"
                       "LEFT JOIN res_company AS c ON c.id=j.company_id\n"
                       "WHERE j.type IN ('bank','cash')" % (self._table,))
        return res

class AccountAbstractPayment(models.AbstractModel):
    _inherit = "account.abstract.payment"

    of_payment_mode_id = fields.Many2one('of.account.payment.mode', string='Payment mode', required=True)
    # journal_id is now related to the payment mode.
    # must be set to readonly or payment creation will try to write in payment mode, with risk of access right error
    # must be set as not required because it is readonly, so not set on the INSERT request
    journal_id = fields.Many2one(related='of_payment_mode_id.journal_id', string='Payment Journal',
                                 required=False, readonly=True, store=True)

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        init_payment_mode = False
        if self._auto:
            cr.execute("SELECT * FROM information_schema.columns WHERE table_name = '%s' AND column_name = 'of_payment_mode_id'" % (self._table,))
            init_payment_mode = not bool(cr.fetchall())

        res = super(AccountAbstractPayment, self)._auto_init()
        if init_payment_mode:
            # Use self.pool as self.env is not yet defined
            comodel_table = self.pool[self._fields['of_payment_mode_id'].comodel_name]._table
            cr.execute("UPDATE %s AS p SET of_payment_mode_id = m.id\n"
                       "FROM %s AS m\n"
                       "WHERE m.journal_id = p.journal_id" % (self._table, comodel_table))
        return res

    @api.model
    def create(self, vals):
        '''
        Allow creation of payments with account journal instead of payment mode.
        In this case, the traceback is printed in logs.
        '''
        try:
            if 'journal_id' in vals and 'of_payment_mode_id' not in vals:
                of_payment_modes = self.env['of.account.payment.mode'].search([('journal_id', '=', vals['journal_id'])], limit=1)
                del vals['journal_id']
                if of_payment_modes:
                    vals['of_payment_mode_id'] = of_payment_modes._ids[0]
                    raise ValidationError(_("Creating payment with account journal instead of payment mode."))
        except ValidationError:
            traceback.print_exc()
        finally:
            return super(AccountAbstractPayment, self).create(vals)

class AccountRegisterPayments(models.TransientModel):
    _name = "account.register.payments"
    _inherit = ["account.register.payments", "account.abstract.payment"]

    def get_payment_vals(self):
        res = super(AccountRegisterPayments, self).get_payment_vals()
        del res['journal_id']
        res['of_payment_mode_id'] = self.of_payment_mode_id.id
        return res

class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "account.abstract.payment"]

    # Champ Ref. du reglement
    of_ref_reglement = fields.Char(size=64, string=u'Réf. du règlement')

    # Champ Categories (Tags)
    of_tag_ids = fields.Many2many('of.payment.tags', string=u'Catégorie', help=u"Sélectionnez la catégorie de paiement")

    @api.multi
    def get_payment_mode_display(self):
        self.ensure_one()

        payment_mode = self.of_payment_mode_id
        result = False

        if payment_mode.config_affichage:
            affichage = self.env['mail.template'].render_template(payment_mode.config_affichage, 'account.payment', self.id, post_process=False)
            result = affichage

        if not result:
            result = _('Paid on %s') % format_date(self.env, self.payment_date)

        return result


class OFPaymentTags(models.Model):
    """ Tags of payment / Catégorie de paiement """
    _name = "of.payment.tags"
    _description = u"Catégorie de paiement"

    name = fields.Char(string=u'Nom catégorie', help=u'Nom catégorie')
    color = fields.Integer(string=u'Couleur')
    tag_description = fields.Text(string=u'Description de la catégorie', help=u'Description de la catégorie de paiement')

    _sql_constraints = [('name_uniq', 'unique (name)', u"Le nom de la catégorie existe déjà !")]

class OFAccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def _of_get_payment_display(self, move_line):
        # Si le paiement n'a pas d'objet paiement (paiement par un avoir, paiement en saisie comptable manuelle, ...),
        #   on affiche  par défaut la référence de l'écriture ou de la pièce comptable.
        # Sinon, on affiche le texte du paiement.
        if not move_line.payment_id:
            result = move_line.ref or move_line.move_id.name
        else:
            result = move_line.payment_id.get_payment_mode_display()
        return result
