# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo import api, fields, models
from datetime import date
from datetime import timedelta
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

NEGATIVE_TERM_OPERATORS = ('!=', 'not like', 'not ilike', 'not in')

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    # Paramètre de la date d'échéance des factures
    of_date_due = fields.Selection([(0, u"Date d'échéance en fonction des conditions de règlement"),
                                    (1, u"Modification manuelle de la date d'échéance possible (non recalcul suivant conditions de règlement si date déjà renseignée)")], string=u"(OF) Date d'échéance")

    @api.multi
    def set_of_date_due_defaults(self):
        return self.env['ir.values'].sudo().set_default('account.config.settings', 'of_date_due', self.of_date_due)

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    of_etiquette_partenaire_ids = fields.Many2many('res.partner.category', related='partner_id.category_id', string=u"Étiquettes client")
    echeance_line_ids = fields.One2many("of.account.echeance", "invoice_id", string="Échéances",order="date_deadline",
                                        readonly=True, states={'draft': [('readonly', False)]},ondelete="cascade")
    echeance_last_amount = fields.Monetary("Montant derniere echeance", currency_field="currency_id", digits=dp.get_precision('Product Price'))
    echeance_last_percent = fields.Float("Pourcentage derniere echeance", digits=dp.get_precision('Product Price'))
    echeance_last_a_jour =  fields.Boolean(u"echeance_last_a_jour",default=True)
    onchange_esc = fields.Boolean("for _onchange_echeance_line_ids")

    @api.onchange("echeance_last_a_jour")
    def _onchange_echeance_last_a_jour(self):
        """Met a jour la derniere ligne d'échéance"""
        if self.onchange_esc or not self.echeance_line_ids:
            self.onchange_esc = False
            self.echeance_last_a_jour = True
            return
        echeances = self.echeance_line_ids
        for echeance in echeances[:-1]:
            if echeance.percent and not echeance.amount: # affecter un montant
                echeance.amount = self.amount_total * echeance.percent / 100
            elif echeance.amount and not echeance.percent: # affecter un pourcentage
                echeance.percent = echeance.amount * 100 / self.amount_total
            elif type(echeance.id) is not int: # le nouveau record a un montant et un pourcentage -> le pourcentage prévaut
                echeance.amount = self.amount_total * echeance.percent / 100
        last_echeance_old = echeances[-1]
        last_echeance_old.percent =  100 - sum(echeances[:-1].mapped('percent'))
        last_echeance_old.amount = self.amount_total - sum(echeances[:-1].mapped('amount'))
        echeances_sorted = sorted(self.echeance_line_ids, key=lambda k: k['date_deadline'])
        last_echeance = echeances_sorted[-1]
        if self.echeance_last_a_jour:# and last_echeance and (last_echeance.percent != self.echeance_last_percent or last_echeance.amount != self.echeance_last_amount):
            vals = {"onchange_esc": True}
            lines_to_add = [(5,0,0)]
            pct_left = 100
            amt_left = self.amount_total
            for echeance in echeances_sorted[:-1]:
                pct_left -= echeance.percent or echeance.amount * 100 / self.amount_total
                amt_left -= echeance.amount or self.amount_total * echeance.percent / 100
                line_vals = {
                    "name": echeance.name,
                    "date_deadline": echeance.date_deadline,
                    "percent": echeance.percent,
                    "amount": echeance.amount,
                    #"last": echeance.last,
                    #"invoice_id": echeance.invoice_id.id,
                }
                lines_to_add.append((0,0,line_vals))
            if amt_left < 0 or pct_left < 0:
                self.echeance_last_a_jour = False
                raise UserError(u"La somme des pourcentages doit être égale à 100")
            last_vals = {
                "name": last_echeance.name,
                "date_deadline": last_echeance.date_deadline,
                "percent": pct_left,
                "amount": amt_left,
                #"last": True,
                #"invoice_id": self.id,
            }
            lines_to_add.append((0,0,last_vals))
            vals["echeance_line_ids"] = lines_to_add
            vals["echeance_last_percent"] = pct_left
            vals["echeance_last_amount"] = amt_left
            self.update(vals)
        #elif not self.echeance_last_a_jour and last_echeance and (last_echeance.percent == self.echeance_last_percent and last_echeance.amount == self.echeance_last_amount):
            # a été passé a False alors que les données sont a jour: on le repasse a True
        #    self.echeance_last_a_jour = True

    # Date d'échéance des factures
    # Surcharge de la méthode pour permettre la comparaison avec le paramètrage du mode de calcul de la date d'échéance (manuel/auto).
    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        param_date_due = self.env['ir.values'].get_default('account.config.settings', 'of_date_due')
        date_invoice = self.date_invoice
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        if not self.payment_term_id:
            # Quand pas de condition de règlement définie
            if (param_date_due and not self.date_due) or not param_date_due or not self.echeance_line_ids:  # On rajoute la vérification pour permettre de modifier manuellement la date d'échéance.
                date_due = self.date_due or self.date_invoice
                vals = {"onchange_esc": True}
                amt = self.amount_total
                pct = 100
                lines_to_add = [(5,0,0)]
                line_vals = {
                    "date_deadline": date_due,
                    "percent": pct,
                    "amount": amt,
                    #"last": True,
                    #"invoice_id": self.id,
                }
                lines_to_add.append((0,0,line_vals))
                vals["echeance_last_percent"] = pct
                vals["echeance_last_amount"] = amt
                vals["echeance_last_a_jour"] = True
                vals["echeance_line_ids"] = lines_to_add
                if (param_date_due and not self.date_due) or not param_date_due:
                    vals["date_due"] = date_due
                self.update(vals)
        else:
            pterm = self.payment_term_id
            pterm_list = pterm.with_context(currency_id=self.company_id.currency_id.id).compute(value=1, date_ref=date_invoice)[0]
            if (param_date_due and not self.date_due) or not param_date_due:  # On rajoute la vérification pour permettre de modifier manuellement la date d'échéance.
                date_due = max(line[0] for line in pterm_list)
                # Ce onchange est appelé aussi au moment de valider la facture
                creer_echeances = True
                if self.echeance_line_ids and len(self.echeance_line_ids) == len(pterm_list): # modifier les echeances existantes
                    creer_echeances = False
                vals = {"onchange_esc": True, "date_due": date_due}
                lines_to_add = [(5,0,0)]
                for i in range(len(pterm_list)):
                    term_line = pterm.line_ids[i]
                    term = pterm_list[i]
                    if creer_echeances:
                        name = term_line.name
                        amt = self.amount_total * term[1]
                        pct = term[1] * 100
                        ddl = term[0]
                    else:
                        name = self.echeance_line_ids[i].name
                        amt = self.echeance_line_ids[i].amount
                        pct = self.echeance_line_ids[i].percent
                        ddl = self.echeance_line_ids[i].date_deadline
                    last = term == pterm_list[len(pterm_list) - 1]
                    line_vals = {
                        "name": name,
                        "date_deadline": ddl,
                        "percent": pct,
                        "amount": amt,
                        #"last": last,
                        "invoice_id": self.id,
                    }
                    lines_to_add.append((0,0,line_vals))
                    if last:
                        vals["echeance_last_percent"] = pct
                        vals["echeance_last_amount"] = amt
                        vals["echeance_last_a_jour"] = True
                vals["echeance_line_ids"] = lines_to_add
                self.update(vals)

    @api.onchange("echeance_line_ids")
    def _onchange_echeance_line_ids(self):
        if self.onchange_esc or not self.echeance_line_ids:
            self.onchange_esc = False
            self.echeance_last_a_jour = True
            return
        old_percent = self.echeance_last_percent
        new_percent = 100 - sum(self.echeance_line_ids[:-1].mapped('percent'))
        old_amount = self.echeance_last_amount
        new_amount = self.amount_total - sum(self.echeance_line_ids[:-1].mapped('amount'))
        #if old_amount != new_amount or old_percent != new_percent:
        self.update({"echeance_last_percent": new_percent,
                     "echeance_last_amount": new_amount,
                     "echeance_last_a_jour": False,
                     })
        if new_percent < 0 or new_amount < 0:
            raise UserError(u"Le pourcentage de la dernière ligne d'échéance doit être supérieur à zéro")

    @api.onchange("amount_total")
    def _onchange_amount_total(self):
        self.echeance_line_ids.compute_amount_from_percent()

    @api.multi
    def recompute_echeances_values(self):
        """
        recalcule les echeances. retire les valeurs des nouvelles a l'ancienne derniere puis recalcule tout. a tester beaucoup ^^"
        """
        echeances = self.echeance_line_ids
        last_echeance = echeances[-1]
        nouvelles = self.env["of.account.echeance"]
        anciennes = self.env["of.account.echeance"]
        pcts_new = 0
        for echeance in echeances:
            if echeance.percent and not echeance.amount: # affecter un montant
                echeance.amount = self.amount_total * echeance.percent / 100
                nouvelles |= echeance
                pcts_new = echeance.percent
            elif echeance.amount and not echeance.percent: # affecter un pourcentage
                echeance.percent = echeance.amount * 100 / self.amount_total
                nouvelles |= echeance
                pcts_new = echeance.percent
            else:
                anciennes |= echeance
        last_old = anciennes[-1]
        last_old.percent -= pcts_new
        last_old.amount = self.amount_total * last_old.percent / 100
        if last_old.percent < 0 or last_old.amount < 0:
            self.echeance_last_a_jour = False
            raise UserError(u"La somme des pourcentages doit être égale à 100")

        pct_left = 100
        amt_left = self.amount_total
        for echeance in echeances[:-1]:
            if echeance.percent and not echeance.amount: # affecter un montant
                echeance.amount = self.amount_total * echeance.percent / 100
            elif echeance.amount and not echeance.percent: # affecter un pourcentage
                echeance.percent = echeance.amount * 100 / self.amount_total
            elif type(echeance.id) is not int: # le nouveau record a un montant et un pourcentage -> le pourcentage prévaut
                echeance.amount = self.amount_total * echeance.percent / 100
            pct_left -= echeance.percent
            amt_left -= echeance.amount
        vals = {"onchange_esc": False, "echeance_last_a_jour": True}
        if amt_left < 0 or pct_left < 0:
            self.echeance_last_a_jour = False
            raise UserError(u"La somme des pourcentages doit être égale à 100")
        last_vals = {
            "percent": pct_left,
            "amount": amt_left,
        }
        echeances[-1].write(last_vals)
        #self.echeance_line_ids.unlink()
        #lines_to_add.append((0,0,last_vals))
        #vals["echeance_line_ids"] = lines_to_add
        vals["echeance_last_percent"] = pct_left
        vals["echeance_last_amount"] = amt_left
        self.write(vals)

    @api.multi
    def write(self,vals):
        super(AccountInvoice,self).write(vals)
        if not vals.get("echeance_last_a_jour",True):
            for invoice in self:
                invoice.recompute_echeances_values()
        return True

    @api.multi
    def action_invoice_open(self):
        """Mettre le libellé des écritures comptables d'une facture avec nom client (30 1er caractères) + no facture"""
        res = super(AccountInvoice, self).action_invoice_open()
        ref = (self.partner_id.name or self.partner_id.parent_id.name or '')[:30] + ' ' + self.number
        self.move_id.line_ids.write({'name': ref})
        self.move_id.write({'ref': ref})
        return res

class AccountAccount(models.Model):
    _inherit = "account.account"

    of_account_counterpart_id = fields.Many2one('account.account', string="Compte de contrepartie")

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def default_get(self, fields_list):
        def get_line_account(line):
            account_id = line['account_id']
            if not account_id:
                return False
            if isinstance(account_id, tuple):
                # Si la ligne existe en db account_id vaut (id, name), sinon c'est un id simple
                account_id = account_id[0]
            return account_obj.browse(account_id)
        journal_obj = self.env['account.journal']
        account_obj = self.env['account.account']

        result = super(AccountMoveLine, self).default_get(fields_list)

        lines = self._context.get('line_ids')
        journal_id = self._context.get('journal_id')
        if not journal_id or not lines:
            return result

        lines = self.env['account.move'].resolve_2many_commands('line_ids', lines, ('account_id', 'debit', 'credit', 'date_maturity'))
        journal = journal_obj.browse(journal_id)
        if journal.type in ('bank', 'cash'):  # pièce comptable de banque ou de caisse
            if len(lines) == 1:
                account = get_line_account(lines[0])
                if account and account.user_type_id.type in ('payable', 'receivable'):
                    if account.user_type_id.type == 'payable':
                        account = journal.default_credit_account_id
                    else:
                        account = journal.default_debit_account_id
                    result.update({
                        'account_id': account and account.id or False,
                        'debit': lines[0]['credit'],
                        'credit': lines[0]['debit'],
                        'date_maturity': lines[0]['date_maturity'],
                    })
        elif journal.type == 'purchase':  # pièce comptable fournisseur
            tax_type = 'purchase'
            len_lines = len(lines)
            if len_lines in (1, 2):
                # resolve_2many_commands ne préserve pas l'ordre des lignes
                # Le nouvel est ordre est [nouvelles lignes (code 0), autres lignes (déjà en DB)]
                # L'ordre est conservé à l'intérieur de ces deux sous-sections
                if lines[-1].get('id') and self._context['line_ids'][-1][0] == 0:
                    lines = lines[::-1]

                account = get_line_account(lines[-1])
                if account:
                    for tax in (account.of_account_counterpart_id.tax_ids if len_lines == 1 else account.tax_ids):
                        if tax.type_tax_use == tax_type:
                            break
                    else:
                        tax = False
                    if tax or len_lines == 1:
                        tax_amount = tax and tax.amount or 0
                        account = account.of_account_counterpart_id if len_lines == 1 else tax.account_id
                        result.update({
                            'account_id': account and account.id or False,
                            'debit': lines[0]['credit'] / (100 + tax_amount) * (100 if len_lines == 1 else tax_amount),
                            'credit': lines[0]['debit'] / (100 + tax_amount) * (100 if len_lines == 1 else tax_amount),
                            'date_maturity': lines[0]['date_maturity'],
                        })
        return result

    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        """Mettre le libellé des écritures comptables d'un paiement avec nom client (30 1er caractères) + no facture"""
        res = super(AccountMoveLine, self).reconcile(writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id)
        filt = self.filtered(lambda line: (line.reconciled or (line.matched_debit_ids and len(line.matched_debit_ids) == 1)) and line.payment_id)
        for line in filt:
            line_ids = self.env['account.move.line']
            if line.account_id.reconcile:
                for reconciled_lines in line.matched_debit_ids:
                    line_ids += reconciled_lines.debit_move_id
                invoice_ids = line_ids.mapped('invoice_id')
                try:
                    line.move_id.write({'ref': line.payment_id.communication or ''})
                except UserError:
                    # Avec le module OCA des verrouillages d'écritures, le write peut générer une erreur
                    # Il ne faut pas qu'elle soit bloquante pour les lettrages
                    pass
                if len(invoice_ids) == 1:
                    name_infos = [(invoice_ids.partner_id.name or invoice_ids.partner_id.parent_id.name or '')[:30], invoice_ids.number]
                    name = (' ').join([text for text in name_infos if text])
                    line.move_id.line_ids.with_context(check_move_validity=False).write({'name': name})
        return res

class AccountMove(models.Model):
    _inherit = "account.move"

    of_export = fields.Boolean(string=u'Exporté')

class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def button_invoices(self):
        """ (smart button facture sur les paiements)
        Choisit les vues en fonctions du type de partenaire
        """
        vals = super(AccountPayment, self).button_invoices()
        if (self.partner_type == "customer"):
            vals['views'] = [(self.env.ref('account.invoice_tree').id, 'tree'),
                             (self.env.ref('account.invoice_form').id, 'form')]
        elif (self.partner_type == "supplier"):
            vals['views'] = [(self.env.ref('account.invoice_supplier_tree').id, 'tree'),
                             (self.env.ref('account.invoice_supplier_form').id, 'form')]
        return vals

    def post(self):
        """Lors d'un lettrage d'un paiement, rajoute le libellé sur toutes les écritures du paiement."""
        res = super(AccountPayment, self).post()
        client_line = self.move_line_ids.filtered(lambda line: line.credit > 0)
        if client_line.name == _("Customer Payment"):
            self.move_line_ids.write({"name":((self.partner_id.name or self.partner_id.parent_id.name or '')[:30] + " " + (self.communication or '')).strip()})  # Permet d'avoir toutes les lignes avec le même libellé
        else:
            self.move_line_ids.write({"name": client_line.name})
        return res

class OFEcheanceLine(models.Model):
    _name = "of.echeance.line"

class OFAccountEcheance(models.Model):
    _name = "of.account.echeance"
    _order = "invoice_id, date_deadline"

    name = fields.Char(string="Nom", required=True, default=u"Échéance")
    date_deadline = fields.Date(string=u"Échéance", required=True)
    invoice_id = fields.Many2one("account.invoice", string="Facture")
    currency_id = fields.Many2one(related="invoice_id.currency_id", readonly=True)
    amount = fields.Monetary(string="Montant", currency_field='currency_id')
    amount_paid = fields.Monetary(string=u"Montant payé", currency_field='currency_id', compute="_compute_amount_paid")
    percent = fields.Float(string=u"Pourcentage", digits=dp.get_precision('Product Price'))
    paid = fields.Boolean(string=u"Payée",compute="_compute_amount_paid")
    last = fields.Boolean(string="Dernière Échéance", compute="_compute_last")
    color = fields.Char("Couleur", compute="_compute_color")
    # booléen pour eviter la boucle infinie de onchange
    onchange_esc = fields.Boolean(string="for onchange")

    @api.multi
    @api.depends('date_deadline')
    def _compute_last(self):
        for invoice in self.mapped('invoice_id'):
            for echeance in invoice.echeance_line_ids:
                echeance.last = echeance == invoice.echeance_line_ids[-1]

    @api.multi
    @api.depends('date_deadline')
    def _compute_color(self):
        date_today = fields.Date.from_string(fields.Date.today())
        for echeance in self:
            date_deadline = fields.Date.from_string(echeance.date_deadline)
            if date_deadline and date_today > date_deadline and not echeance.paid:
                echeance.color = "red"
            else:
                echeance.color = "black"

    @api.multi
    def compute_amount_from_percent(self):
        u"""fonction appelée quand le montant total de la facture change, pour recalculer les montants"""
        for invoice in self.mapped("invoice_id"):
            for echeance in invoice.echeance_line_ids:
                vals = {"amount": invoice.amount_total * echeance.percent / 100,"onchange_esc":True}
                echeance.update(vals)

    @api.multi
    @api.depends("invoice_id","invoice_id.amount_total",
                 "invoice_id.residual","invoice_id.state")
    def _compute_amount_paid(self):
        u"""Prend en compte le Montant payé de la facture et alloue ce montant au échéances par ordre chronologique"""
        for invoice in self.mapped('invoice_id'):
            invoice._compute_residual()
            residual = invoice.residual
            if invoice.state == "draft":
                residual = invoice.amount_total
            amount_paid_left = invoice.amount_total - residual
            for echeance in invoice.echeance_line_ids:
                amount_paid =  min(echeance.amount, amount_paid_left)
                if amount_paid == echeance.amount and amount_paid > 0:
                    paid = True
                else:
                    paid = False
                vals = {"amount_paid": amount_paid, "paid": paid}
                echeance.update(vals)
                amount_paid_left -= amount_paid

    @api.onchange("amount")
    def _onchange_amount(self):
        """Met a jour le pourcentage en fonction du montant"""
        self.ensure_one()
        if self.last:
            self.onchange_esc = False
            return
        old_percent = self.percent # supprimer ou mettre dans le if old_amount != new_amount
        if self.invoice_id.amount_total == 0:
            new_percent = False
        else:
            new_percent = self.amount * 100 / self.invoice_id.amount_total
        if not self.onchange_esc:
            vals = {"percent": new_percent,"onchange_esc":True}
            self.update(vals)
        else:
            self.onchange_esc = False

    @api.onchange("percent")
    def _onchange_percent(self):
        """Met a jour le montant en fonction du pourcentage"""
        self.ensure_one()
        if self.last:
            self.onchange_esc = False
            return
        old_amount = self.amount # supprimer ou mettre dans le if old_amount != new_amount
        new_amount = self.invoice_id.amount_total * self.percent / 100
        if not self.onchange_esc:
            vals = {"amount": new_amount,"onchange_esc":True}
            self.update(vals)
        else:
            self.onchange_esc = False

    @api.model
    def compute_last_values_invoice(self,invoice_id):
        """Met a jour la derniere échéance lors du write"""
        echeances = self.search([("invoice_id","=",invoice_id.id)],order="date_deadline")
        if not echeances:
            return
        last_echeance = echeances[-1]
        percent_left = 100
        montant_left = invoice_id.amount_total
        for i in range(0,len(echeances)-1):
            percent_left -= echeances[i].percent
            montant_left -= echeances[i].amount
        if percent_left < 0 or montant_left < 0:
            raise UserError(u"Incohérence de données. La somme des pourcentages des échéances doit être égale à 100")
        vals = {"amount": montant_left, "percent": percent_left}
        last_echeance.write(vals)

    """@api.multi
    def write(self,vals):
        super(OFAccountEcheance, self).write(vals)
        "" "if not vals.get("invoice_id",True):
            self.unlink()
            return True"" "
        la_line = False
        if len(self) > 0:
            la_line = self[0]
        # mettre a jour percent et amount
        if la_line and la_line.invoice_id and not la_line.last and (vals.get("amount",False) or vals.get("percent",False)):
            #self.env["of.account.echeance"].compute_last_values_invoice(la_line.invoice_id)
            la_line.invoice_id.echeance_last_a_jour = True
        return True"""

    """@api.multi
    def unlink(self):
        for invoice in self.mapped('invoice_id'):
            invoice.echeance_last_a_jour = False
        super(OFAccountEcheance, self).unlink()"""

class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    name = fields.Char(string="Nom",required=True,default=u"Échéance")
