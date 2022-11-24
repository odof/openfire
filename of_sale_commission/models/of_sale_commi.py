# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.exceptions import UserError


class OFSaleCommi(models.Model):
    _name = "of.sale.commi"
    _description = "Commissions sur les ventes"

    name = fields.Char(string=u"Libellé")
    type = fields.Selection(
        [('acompte', "Acompte"), ('solde', "Solde"), ('avoir', "Avoir")], string="Type"
    )
    user_id = fields.Many2one(
        'res.users', string="Commercial", required=True,
        domain="[('of_profcommi_id', '!=', False)]"
    )
    partner_id = fields.Many2one('res.partner', string="Client", compute="_compute_partner_id", store=True)
    company_id = fields.Many2one('res.company', string=u"Société", compute="_compute_company_id", store=True)
    date_valid = fields.Date(string="Date de validation")
    date_paiement = fields.Date(string="Date de paiement")
    state = fields.Selection(
        [
            ('draft', "Brouillon"),
            ('paid', u"Payé"),
            ('to_pay', u"À payer"),
            ('cancel', u"Annulé"),
            ('to_cancel', u"À annuler"),
            ('paid_cancel', u"Payé annulé"),
        ], string=u"État", required=True, default='draft'
    )
    total_vente = fields.Float(compute="_compute_total_vente", string="Total ventes HT")
    total_commi = fields.Float(compute="_compute_total_commi", string="Total commissions")
    total_du = fields.Float(string="Commission due")
    commi_line_ids = fields.One2many('of.sale.commi.line', 'commi_id', string="Lignes commission")
    order_id = fields.Many2one('sale.order', string="Bon de commande", readonly=True)
    invoice_id = fields.Many2one('account.invoice', string="Facture", readonly=True)
    inv_commi_id = fields.Many2one('of.sale.commi', u"Commission associée")
    cancel_commi_id = fields.Many2one('of.sale.commi', u"Commission annulée")
    order_commi_ids = fields.One2many('of.sale.commi', 'inv_commi_id', string=u'Commissions associées')
    compl_du = fields.Float(compute="_compute_compl_du", string=u"Commission versée")
    total_du_b = fields.Float(compute="_compute_total_du_b", string="Commission Due")

    @api.depends('order_id', 'invoice_id', 'order_id.partner_id', 'invoice_id.partner_id')
    def _compute_partner_id(self):
        for commi in self:
            if commi.type == 'acompte':
                commi.partner_id = commi.order_id.partner_id
            else:
                commi.partner_id = commi.invoice_id.partner_id

    @api.depends('order_id', 'invoice_id', 'order_id.company_id', 'invoice_id.company_id')
    def _compute_company_id(self):
        for commi in self:
            if commi.type == 'acompte':
                commi.company_id = commi.order_id.company_id
            else:
                commi.company_id = commi.invoice_id.company_id

    @api.depends('order_id.amount_untaxed', 'invoice_id.amount_untaxed')
    def _compute_total_vente(self):
        for commi in self:
            if commi.type == 'acompte':
                sign = commi.cancel_commi_id and -1 or 1
                commi.total_vente = commi.order_id.amount_untaxed * sign
            else:
                invoice = commi.invoice_id
                orders = invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
                if orders:
                    invoices = orders.mapped('order_line').mapped('invoice_lines').mapped('invoice_id')
                    total_vente = sum(invoices.mapped('amount_untaxed'))
                else:
                    total_vente = invoice.amount_untaxed_signed
                # Si le module of_sale_prorata est installé, il faut retirer la retenue de garantie
                # :todo: calculer avec la somme des lignes de commi
                commi.total_vente = total_vente

    @api.depends('commi_line_ids.px_commi')
    def _compute_total_commi(self):
        for commi in self:
            if commi.cancel_commi_id:
                # Sur une commission d'annulation de commission sur acompte, le montant total est
                commi.total_commi = -sum(round(line.px_commi, 2) for line in commi.cancel_commi_id.commi_line_ids)
            else:
                commi.total_commi = sum(round(line.px_commi, 2) for line in commi.commi_line_ids)

    @api.depends('order_commi_ids.total_du')
    def _compute_compl_du(self):
        for commi in self:
            if commi.type == 'solde':
                compl_du = sum(compl.total_du for compl in commi.order_commi_ids)
                commi.compl_du = compl_du
                commi.total_du = commi.total_commi - compl_du
            else:
                commi.compl_du = 0

    @api.onchange('total_commi', 'compl_du')
    def _compute_total_du_b(self):
        for commi in self:
            if commi.type != 'acompte':
                commi.total_du_b = commi.total_commi - commi.compl_du

    @api.multi
    def action_to_pay(self):
        commis = self.filtered(lambda commi: commi.state == 'draft')
        commis_date = commis.filtered(lambda commi: not commi.date_valid)
        commis.write({'state': 'to_pay'})
        commis_date.write({'date_valid': fields.Date.today()})

    @api.multi
    def action_cancel(self):
        for commi in self:
            self.create({
                'name': commi.name,
                'state': 'to_cancel',
                'user_id': commi.user_id.id,
                'type': 'acompte',
                'total_du': -commi.total_du,
                'date_valid': fields.Date.today(),
                'order_id': commi.order_id.id,
                'cancel_commi_id': commi.id,
            })

    @api.multi
    def get_total_du(self):
        self.ensure_one()
        if self.type == 'solde':
            # On verse la totalité de la commission, moins ce qui a déjà été versé
            return self.total_commi - (self.compl_du or 0)
        if type == 'avoir':
            return self.total_commi
        # Type acompte
        profil = self.user_id.of_profcommi_id
        if not profil:
            return 0

        # Variable acompte utilisable dans les formules
        acompte = 0
        if len(self.order_id.of_echeance_line_ids) > 1:
            acompte = self.order_id.of_echeance_line_ids[0].amount

        taux_acompte = profil.taux_acompte
        for profil_line in profil.profcommi_line_ids.filtered(lambda line: line.type == 'acompte'):
            cond = False
            exec profil_line.regcommi_id.code
            if cond:
                taux_acompte = profil_line.taux_commi
                break
        return round(self.total_commi * taux_acompte / 100.0, 2)

    @api.onchange('commi_line_ids')
    def onchange_line(self):
        self.total_du = self.get_total_du()

    @api.multi
    def _create_line(self, src_line, taux_zero):
        """
        Cree une ligne de commission correspondant a src_line pour commi, sans mettre commi a jour
        """
        self.ensure_one()
        if taux_zero:
            taux_commi = 0
            px_commi = 0
        else:
            taux_commi = self.user_id.of_profcommi_id.get_taux_commi(src_line)
            px_commi = round(src_line.price_subtotal * taux_commi / 100.0, 2)

        line_data = {
            'commi_id': self.id,
            'taux_commi': taux_commi,
        }
        if self.type == 'acompte':
            line_data.update({
                'order_line_id': src_line.id,
                'px_commi': px_commi,
            })
        elif self.type == 'solde':
            line_data.update({
                'invoice_line_id': src_line.id,
                'px_commi': px_commi,
            })
        else:  # type == 'avoir'
            line_data.update({
                'invoice_line_id': src_line.id,
                'px_commi': -px_commi,
            })
        self.env['of.sale.commi.line'].create(line_data)

    @api.multi
    def create_lines(self, source_lines, taux_zero=False):
        """
        Cree pour commi les lignes de commission referencant source_lines, si inexistantes
        """
        self.ensure_one()
        if self.type == 'acompte':
            existing_lines = self.commi_line_ids.mapped('order_line_id')
        else:
            existing_lines = self.commi_line_ids.mapped('invoice_line_id')
        for src_line in source_lines - existing_lines:
            self._create_line(src_line, taux_zero)

        self.total_du = self.get_total_du()

    @api.multi
    def update_commi(self, filtre=None):
        for commi in self:
            if commi.type == 'acompte':
                source = commi.order_id
                source_lines = source.order_line

                def line_source(commi_line):
                    return commi_line.order_line_id
            else:
                source = commi.invoice_id
                source_lines = source.invoice_line_ids

                def line_source(commi_line):
                    return commi_line.invoice_line_id

            for line in commi.commi_line_ids:
                if line_source(line) in source_lines:
                    line.update_line(filtre)
                else:
                    line.unlink()
            commi.create_lines(source_lines)

    @api.multi
    def make_commi_invoice_lines_from_old(self, commis_old, invoice, profil, commi_type='solde', inverse=False):
        u"""
        Retourne les données des lignes de commissions a créer pour la commission courrante
            en se basant sur celles de la commission d'id commi_old_id
            et sur la facture associée à la nouvelle commission
        :param commis_old: liste des ids des commissions servant de modèles
        :param invoice: facture associée à la nouvelle commission
        :param profil: profil de vendeur, utilise pour les lignes d'invoice n'ayant pas de correspondance
                        dans l'ancienne commission
        :param commi_type: 'solde' ou 'avoir'
        :param inverse: indique si les sommes doivent être inversées (avoir sur facture ou avoir sur avoir)
        :return:
        """
        commi_lines_data = []
        utilises = self.env['of.sale.commi.line']
        old_commi_lines = self.env['of.sale.commi.line']

        if commis_old:
            old_commi_lines = commis_old.mapped('commi_line_ids')

        for inv_li in invoice.invoice_line_ids:
            # On récupère les lignes de commission de la commande order ayant le même produit et
            # le même montant HT que la ligne de facture
            old_commi_line = False

            for line in old_commi_lines:
                if line.product_id == inv_li.product_id and line not in utilises:
                    utilises |= line
                    old_commi_line = line
                    break

            if old_commi_line:
                taux_commi = old_commi_line.taux_commi
                px_commi = old_commi_line.px_commi
                if inverse:
                    px_commi = -px_commi
            else:
                taux_commi = profil.get_taux_commi(inv_li)
                px_commi = round(inv_li.price_subtotal * taux_commi / 100.0, 2)
                if type == 'avoir':
                    px_commi = -px_commi

            commi_lines_data.append({
                'commi_id': isinstance(self.id, (int, long)) and self.id,
                'type': commi_type,
                'invoice_line_id': inv_li.id,
                'product_id': inv_li.product_id.id,
                'qty': inv_li.quantity,
                'prix_vente': inv_li.price_subtotal,
                'taux_commi': taux_commi,
                'px_commi': px_commi,
            })

        return commi_lines_data

    @api.onchange('user_id')
    def onchange_user_id(self):
        """
        Retourne les lignes de commission correspondant a la source "source" de type "type" pour le vendeur "vendeur"
        """
        commi_line_obj = self.env['of.sale.commi.line']
        if not self.user_id:
            return
        profil = self.user_id.of_profcommi_id
        if not profil:
            raise UserError(u"Cet utilisateur ne dispose pas d'un profil de commissionnement.")

        if self.type == 'acompte':
            order = self.order_id

            # On rattache la commission à la première trouvée pour le même vendeur dans une facture liée.
            commi_inv_compl = False
            for invoice in order.invoice_ids:
                if invoice.type == 'out_invoice':
                    for commi_solde in invoice.of_commi_ids:
                        if commi_solde.user_id == self.user_id:
                            commi_inv_compl = commi_solde.id
                            break
                    else:
                        continue
                    break

            # Les lignes de commissions sont régénérées
            commi_lines = commi_line_obj
            for order_line in order.order_line:
                taux_commi = profil.get_taux_commi(order_line)
                commi_lines |= commi_line_obj.new({
                    'commi_id': self.id,
                    'type': 'acompte',
                    'order_line_id': order_line.id,
                    'product': order_line.product_id.id,
                    'qty': order_line.product_uom_qty,
                    'prix_vente': order_line.price_subtotal,
                    'taux_commi': taux_commi,
                    'px_commi': round(order_line.price_subtotal * taux_commi / 100.0, 2),
                })

            self.inv_commi_id = commi_inv_compl
            self.commi_line_ids = commi_lines
        elif self.type == 'solde':
            invoice = self.invoice_id
            orders = invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')

            order_commis = self.env['of.sale.commi']
            compl_du = 0

            for order in orders:
                for commi_ac in order.get_active_commis():
                    if commi_ac.user_id == self.user_id and commi_ac.inv_commi_id | self == self:
                        order_commis |= commi_ac
                        compl_du += commi_ac.total_du
                        break
            if order_commis:
                self.update({
                    'order_commi_ids': order_commis,
                    'compl_du': compl_du,
                    'commi_line_ids': self.make_commi_invoice_lines_from_old(order_commis, invoice, profil),
                })
            else:
                # Aucune commission 'acompte' ne correspond
                self.update({
                    'compl_du': 0,
                    'commi_line_ids': self.make_commi_invoice_lines_from_old(False, invoice, profil),
                })
        else:
            # Normalement les commissions sur avoirs sont créées d'origine, ce cas ne devrait se produire
            # que très rarement (erreur de manipulation).
            # Il n'est pas évident de récupérer la facture associée, on va donc directement recalculer les lignes
            invoice = self.invoice_id
            self.update({
                'compl_du': 0,
                'commi_line_ids': self.make_commi_invoice_lines_from_old(False, invoice, profil, 'avoir', True),
            })

    @api.multi
    def recalc_total_du(self):
        for commi in self:
            commi.total_du = commi.total_commi - commi.compl_du

    @api.multi
    def copy_data(self, default=None):
        # Désactivation de la création de commission par copie
        return False

    @api.model
    def create(self, vals):
        if 'name' not in vals:
            if vals.get('order_id'):
                vals['name'] = self.env['sale.order'].browse(vals['order_id']).name
            elif vals.get('invoice_id'):
                invoice = self.env['account.invoice'].browse(vals['invoice_id'])
                vals['name'] = invoice.origin or invoice.reference
        commi = super(OFSaleCommi, self).create(vals)
        if vals.get('inv_commi_id'):
            commi.inv_commi_id.recalc_total_du()
        return commi

    @api.multi
    def write(self, vals):
        if not self:
            return True
        # self.check_commi_access_rights()
        for commi in self:
            if commi.type == 'acompte':
                inv_commi_old = False
                if 'inv_commi_id' in vals:
                    inv_commi_old = commi.inv_commi_id

                result = super(OFSaleCommi, self).write(vals)

                if inv_commi_old:
                    inv_commi_old.recalc_total_du()
                if commi.inv_commi_id:
                    commi.inv_commi_id.recalc_total_du()
            else:
                result = super(OFSaleCommi, commi).write(vals)
        return result

    @api.multi
    def unlink(self):
        to_recalc = self.env['of.sale.commi']
        for commi in self:
            if commi.state in ('paid', 'paid_cancel'):
                raise UserError(u'Vous ne pouvez pas supprimer une commission qui a déjà été payée')
            if commi.type == 'acompte' and commi.inv_commi_id:
                to_recalc |= commi.inv_commi_id
        res = super(OFSaleCommi, self).unlink()
        to_recalc.recalc_total_du()
        return res


class OFSaleCommiLine(models.Model):
    _name = "of.sale.commi.line"
    _description = "Lignes de commission"

    commi_id = fields.Many2one('of.sale.commi', string='Commission', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', compute='_compute_product_id', string="Article")
    qty = fields.Float(compute="_compute_qty", string=u"Quantité")
    prix_vente = fields.Float(compute='_compute_prix_vente', string="Prix de vente")
    taux_commi = fields.Float(string='Taux Commission')
    px_commi = fields.Float(string='Commission Totale')
    order_line_id = fields.Many2one('sale.order.line', 'Ligne de commande', readonly=True)
    invoice_line_id = fields.Many2one('account.invoice.line', 'Ligne de facture', readonly=True)
    type = fields.Selection(related='commi_id.type', readonly=True, string='Type')

    def _compute_product_id(self):
        for line in self:
            if line.type == 'acompte':
                line.product_id = line.order_line_id.product_id
            else:
                line.product_id = line.invoice_line_id.product_id

    def _compute_qty(self):
        for line in self:
            if line.type == 'acompte':
                line.qty = line.order_line_id.product_uom_qty
            else:
                line.qty = line.invoice_line_id.quantity

    def _compute_prix_vente(self):
        for line in self:
            if line.type == 'acompte':
                line.prix_vente = line.order_line_id.price_subtotal
            else:
                line.prix_vente = line.invoice_line_id.price_subtotal

    @api.onchange('taux_commi')
    def onchange_taux_commi(self):
        mult = self.type == 'avoir' and -1 or 1
        self.px_commi = mult * round(self.prix_vente * self.taux_commi / 100.0, 2)

    @api.onchange('px_commi')
    def onchange_prix_commi(self):
        mult = self.type == 'avoir' and -1 or 1
        self.taux_commi = self.prix_vente and mult * round(self.px_commi * 100.0 / self.prix_vente, 2)

    @api.multi
    def update_line(self, filtre=None):
        """
        filtre contient les ids des lignes de facture dont le taux de commissionnement doit être recalculé
         (ex: le produit a changé)
        Si filtre n'existe pas, tous seront recalculés
        """
        self.ensure_one()
        source = self.order_line_id if self.type == 'acompte' else self.invoice_line_id
        if source.price_subtotal == 0:
            self.write({
                'taux_commi': 1,
                'px_commi': 0
            })
        else:
            signe = self.type == 'avoir' and -1 or 1
            px_commi = signe * round(source.price_subtotal * self.taux_commi / 100.0, 2)
            taux_commi = signe * round(100.0 * self.px_commi / source.price_subtotal, 2)

            if self.px_commi != px_commi and self.taux_commi != taux_commi:
                # Le prix a changé, on met à jour la commission
                if filtre is None or (source.id in filtre):
                    taux_commi = self.commi_id.user_id.of_profcommi_id.get_taux_commi(source)
                    px_commi = round(source.price_subtotal * taux_commi / 100, 2)
                    if taux_commi != self.taux_commi or px_commi != self.px_commi:
                        self.write({
                            'taux_commi': taux_commi,
                            'px_commi': signe * px_commi
                        })
                else:
                    px_commi = round(source.price_subtotal * self.taux_commi / 100, 2)
                    self.write({
                        'px_commi': signe * px_commi
                    })
