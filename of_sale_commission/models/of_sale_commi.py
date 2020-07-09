# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError
import itertools


class OFSaleRegcommi(models.Model):
    _name = "of.sale.regcommi"
    _description = u"Règles de commissions"

    name = fields.Char(string=u"Libellé")
    code = fields.Text(string="Code")

    _sql_constraints = [
        ('name_id_unique', 'unique (name)', u"Le libellé est déjà utilisé !"),
    ]

    @api.model
    def create(self, vals):
        if self._uid != SUPERUSER_ID:
            raise UserError(u"Seul l'administrateur a le droit de créer des règles !")
        return super(OFSaleRegcommi, self).create(vals)

    @api.multi
    def write(self, vals):
        if self._uid != SUPERUSER_ID:
            raise UserError(u"Seul l'administrateur a le droit de modifier des règles !")
        return super(OFSaleRegcommi, self).write(vals)


class OFSaleProfcommi(models.Model):
    _name = "of.sale.profcommi"
    _description = "Profils de commissions"

    name = fields.Char(string="Profil")
    taux_commi = fields.Float(string="Taux global", digits=(16, 2), default=4)
    taux_acompte = fields.Float(string="Indice acompte", default=50)
    taux_solde = fields.Float(string=u"Indice règlement", compute="_compute_taux_solde")
    profcommi_line_ids = fields.One2many('of.sale.profcommi.line', 'profcommi_id', string="Commissions")
    user_ids = fields.One2many('res.users', 'of_profcommi_id', string="Utilisateurs", readonly=True)

    @api.depends('taux_acompte')
    def _compute_taux_solde(self):
        for profcommi in self:
            profcommi.taux_solde = 100 - profcommi.taux_acompte

    _sql_constraints = [
        ('name_id_unique', 'unique (name)', u"Le libellé est déjà utilisé !"),
    ]

    @api.multi
    def get_taux_commi(self, line):
        """
        Recupere le taux de commissionnement pour un profil de commission et une ligne
        type definit le type de ligne : 'acompte' pour order_line, 'solde' ou 'avoir' pour invoice_line
        """
        self.ensure_one()
        taux = self.taux_commi
        product = line.product_id  # A utiliser dans les règles de commissionnement (regcommi_id.code)
        cond = False
        for prof_line in self.profcommi_line_ids:
            if prof_line.type == 'commission':
                exec prof_line.regcommi_id.code
                if cond:
                    taux = prof_line.taux_commi
                    break
        return taux


class OFSaleProfcommiLine(models.Model):
    _name = "of.sale.profcommi.line"
    _description = "Ligne de Profil Commissions"
    _order = "type,sequence"

    name = fields.Char(string=u"Libellé", required=True)
    profcommi_id = fields.Many2one('of.sale.profcommi', string="Profil", ondelete='cascade')
    regcommi_id = fields.Many2one('of.sale.regcommi', string=u"Règle", required=True, ondelete='restrict')
    sequence = fields.Integer(string=u"Séquence")
    taux_commi = fields.Float(string="Pourcentage", digits=(16, 2), default=4)
    type = fields.Selection(
        [('commission', "Taux de Commission"), ('acompte', "Premier Versement")], string="Type", required=True,
        default="commission"
    )


class ResUsers(models.Model):
    _inherit = 'res.users'

    of_profcommi_id = fields.Many2one('of.sale.profcommi', string="Profil Commissions", ondelete='restrict')


class OFSaleCommi(models.Model):
    _name = "of.sale.commi"
    _description = "Commissions sur les ventes"

    name = fields.Char(string=u"Libellé")
    type = fields.Selection(
        [('acompte', "Acompte"), ('solde', "Solde"), ('avoir', "Avoir")], string="Type"
    )
    user_id = fields.Many2one('res.users', string="Commercial", required=True)
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
                # Sur une commission d'annulation de commission sir acompte, le montant total est
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
            # On verse la totalite de la commission, moins ce qui a deja ete verse
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
            commi_lines = commi_line_obj
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
            # Normalement les commissions sur avoirs sont créés d'origine, ce cas ne devrait se produire
            # que très rarement (erreur de manipulation).
            # Il n'est pas évident de récupérer la facture associee, on va donc directement recalculer les lignes
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
        # Desactivation de la creation de commission par copie
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
    qty = fields.Float(compute="_compute_qty", string="Quantite")
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


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_commi_ids = fields.One2many('of.sale.commi', 'order_id', string="Commissions vendeurs")
    of_nb_commis = fields.Integer(compute="_compute_nb_commis", string="Nb. Commissions")

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
        # En cas de modification de l'échéancier, recalcul des commissions
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
        if 'of_echeance_line_ids' in vals:
            # Recalcul du montant dû des commissions
            for order in orders:
                for commi in self.mapped('of_commi_ids'):
                    commi.total_du = commi.get_total_du()
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
        action['domain'] = ['|', ('order_id', 'in', self.ids), ('inv_commi_id.order_id', 'in', self.ids)]
        action['context'] = {
            'default_type': 'acompte',
            'default_order_id': len(self) == 1 and self.id,
        }
        return action


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    of_commi_ids = fields.One2many('of.sale.commi', 'invoice_id', string="Commissions vendeurs")
    of_nb_commis = fields.Integer(compute="_compute_nb_commis", string="Nb. Commissions")

    @api.depends('of_commi_ids')
    def _compute_nb_commis(self):
        for invoice in self:
            invoice.of_nb_commis = len(invoice.of_commi_ids)

    @api.multi
    def copy(self, default=None):
        result = super(AccountInvoice, self).copy(default=default)
        if self.type not in ('out_invoice', 'out_refund'):
            return result

        commi_obj = self.env['of.sale.commi'].sudo()
        commi_line_obj = self.env['of.sale.commi.line']
        new_invoice = self.browse(result)

        for commi_orig in self.sudo().of_commi_ids:
            if commi_orig.state in ('draft', 'to_pay', 'paid'):
                commi = commi_obj.create({
                    'name': new_invoice.reference,
                    'state': 'draft',
                    'user_id': commi_orig.user_id.id,
                    'type': commi_orig.type,
                    'invoice_id': new_invoice.id,
                })

                commi_lines_data = commi.make_commi_invoice_lines_from_old(commi_orig, new_invoice,
                                                                           commi.user_id.of_profcommi_id,
                                                                           commi.type, False)
                for commi_line_data in commi_lines_data:
                    commi_line_obj.create(commi_line_data)

                # Ne va créer aucune ligne, mais mettra à jour les totaux
                commi.create_lines(new_invoice.invoice_line_ids)
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
                    'order_commi_ids': [(6, 0, commi_orig.order_commi_ids.ids)],
                })

                commi_lines_data = commi.make_commi_invoice_lines_from_old(commi_orig, invoice,
                                                                           commi.user_id.of_profcommi_id,
                                                                           commi.type, False)
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

        # Recalcul des acomptes pour les lignes de facture modifiées
        recalc_filtre = [
            inv_val[1]
            for inv_val in vals.get('invoice_line_ids', [])
            if inv_val[0] == 1 and 'product_id' in inv_val[2]
        ]
        self.sudo().mapped('of_commi_ids').update_commi(recalc_filtre)
        return result

    @api.multi
    def confirm_paid(self):
        super(AccountInvoice, self).confirm_paid()
        draft_commis = self.mapped('of_commi_ids').filtered(lambda commi: commi.state == 'draft')
        draft_commis.action_to_pay()

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
        self.env['sale.order'].search(['|',
                                       ('partner_id', 'in', partner_ids),
                                       ('partner_invoice_id', 'in', partner_ids)]).of_verif_acomptes()
        super(AccountInvoice, self)._compute_payments()

    @api.multi
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None):
        self = self.with_context(of_commis_to_refund=False)
        refunds = super(AccountInvoice, self).refund(date_invoice=date_invoice, date=date, description=description,
                                                     journal_id=journal_id)
        commi_obj = self.env['of.sale.commi']
        commi_line_obj = self.env['of.sale.commi.line']

        refund_mode = self._context.get('refund_mode')
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

                    commi_lines_data = commi.make_commi_invoice_lines_from_old(commi_inv, refund,
                                                                               commi_inv.user_id.of_profcommi_id,
                                                                               type, True)
                    for commi_line_data in commi_lines_data:
                        commi_line_obj.create(commi_line_data)
                    # Ne va créer aucune ligne, mais mettra a jour les totaux
                    commi.create_lines(refund.invoice_line_ids)
        return refunds

    @api.multi
    def unlink(self):
        self.mapped('of_commi_ids').unlink()
        return super(AccountInvoice, self).unlink()

    @api.multi
    def action_view_commissions(self):
        action = self.env.ref('of_sale_commission.action_of_sale_commi_tree').read()[0]
        action['domain'] = ['|', ('invoice_id', 'in', self.ids), ('order_commi_ids.order_id', 'in', self.ids)]
        commi_type = 'solde' if self.type == 'out_invoice' else 'avoir'
        action['context'] = {
            'default_type': commi_type,
            'default_invoice_id': len(self) == 1 and self.id,
        }
        return action

    @api.model
    def _get_refund_modify_read_fields(self):
        fields = super(AccountInvoice, self)._get_refund_modify_read_fields()
        if self._context.get('of_commis_to_refund'):
            fields.append('of_commi_ids')
        return fields


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    @api.multi
    def compute_refund(self, mode='refund'):
        commis = False
        if mode == 'modify':
            # Les commissions sont à répercuter sur la facture finale.
            commis = self.env['of.sale.commi'].sudo()\
                .search([('invoice_id', 'in', self._context.get('active_ids', [])),
                         ('state', '!=', 'cancel')])

        return super(AccountInvoiceRefund, self.with_context(of_commis_to_refund=commis,
                                                             refund_mode=mode)).compute_refund(mode=mode)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def write(self, vals):
        orders = self.env['sale.order']
        if 'order_ids' in vals:
            orders = self.mapped('order_ids')
        res = super(AccountPayment, self).write(vals)
        if 'order_ids' in vals or 'active' in vals or 'state' in vals:
            orders |= self.mapped('order_ids')
        if orders:
            orders.of_verif_acomptes()
        return res


class GestionPrix(models.TransientModel):
    _inherit = 'of.sale.order.gestion.prix'

    @api.multi
    def calculer(self, simuler=False):
        super(GestionPrix, self).calculer(simuler=simuler)
        if not simuler:
            self.order_id.of_commi_ids.filtered(
                lambda commi: (commi.total_du >= 0 and
                               commi.state not in ('paid', 'to_cancel', 'cancel', 'paid_cancel'))
            ).update_commi()
