# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _auto_init(self):
        cr = self._cr
        if self._auto:
            cr.execute(
                "SELECT * "
                "FROM information_schema.columns "
                "WHERE table_name = '%s' "
                "AND column_name = 'of_amount_to_invoice_no_prorata'" % self._table)
            if not bool(cr.fetchall()):
                cr.execute(
                    "ALTER TABLE sale_order ADD COLUMN of_amount_to_invoice_no_prorata numeric"
                )
                # Reste à facturer
                categ_id = self.env['ir.values'].get_default(
                    'sale.config.settings', 'of_deposit_product_categ_id_setting') or 0
                product_ids = (
                    self.env['ir.values'].get_default('sale.config.settings', 'of_product_prorata_id_setting') or 0,
                    self.env['ir.values'].get_default('sale.config.settings', 'of_product_retenue_id_setting') or 0,
                )
                self.env.cr.execute(
                    "WITH sub AS ("
                    "    SELECT sol.order_id, SUM(sol.of_amount_to_invoice) AS of_amount_to_invoice "
                    "    FROM sale_order_line AS sol "
                    "      LEFT JOIN product_product AS pp ON pp.id=sol.product_id "
                    "      LEFT JOIN product_template AS pt ON pt.id=pp.product_tmpl_id "
                    "    WHERE pt.categ_id != %s "
                    "      AND sol.product_id NOT IN %s "
                    "    GROUP BY sol.order_id "
                    ") "
                    "UPDATE sale_order AS so "
                    "SET of_amount_to_invoice_no_prorata = sub.of_amount_to_invoice "
                    "FROM sub "
                    "WHERE sub.order_id=so.id", (categ_id, product_ids)
                )
        res = super(SaleOrder, self)._auto_init()
        return res

    of_prorata_percent = fields.Float(string=u"Compte prorata(%)", digits=(4, 5))
    of_retenue_garantie_pct = fields.Float(
        string=u"Ret. garantie(%)", digits=(4, 5),
        help=u"Retenue calculée depuis le montant total de la commande")
    of_prochaine_situation = fields.Integer(
        compute='_compute_of_prochaine_situation', string=u"Prochaine situation",
        help=u"Situation pour laquelle la prochaine facture sera générée")
    of_last_situation = fields.Boolean(compute='_compute_of_last_situation', string=u"Dernière situation ?")
    of_nb_situations = fields.Integer(string=u"Nb. situations")
    of_amount_to_invoice_no_prorata = fields.Float(
        string=u"Reste à facturer hors acompte, RG et prorata",
        compute="_compute_of_amount_to_invoice_no_prorata", store=True
    )

    @api.depends()
    def _compute_of_prochaine_situation(self):
        product_situation_id = self.env['ir.values'].get_default(
            'sale.config.settings', 'of_product_situation_id_setting')
        for order in self:
            n = 1
            if product_situation_id:
                for invoice in order.invoice_ids:
                    if invoice.state == 'cancel':
                        continue
                    for line in invoice.invoice_line_ids:
                        if line.product_id.id == product_situation_id:
                            n += invoice.type == 'out_invoice' and 1 or -1
                            break
            order.of_prochaine_situation = n

    @api.depends('of_prochaine_situation', 'of_nb_situations')
    def _compute_of_last_situation(self):
        for order in self:
            order.of_last_situation = order.of_prochaine_situation == order.of_nb_situations

    @api.depends('order_line.of_amount_to_invoice')
    def _compute_of_amount_to_invoice_no_prorata(self):
        categ_id = self.env['ir.values'].get_default('sale.config.settings', 'of_deposit_product_categ_id_setting')
        product_ids = [
            self.env['ir.values'].get_default('sale.config.settings', 'of_product_prorata_id_setting'),
            self.env['ir.values'].get_default('sale.config.settings', 'of_product_retenue_id_setting'),
        ]
        for record in self:
            record.of_amount_to_invoice_no_prorata = sum(
                record.order_line.filtered(
                    lambda l: l.product_id.categ_id.id != categ_id and l.product_id.id not in product_ids
                ).mapped('of_amount_to_invoice')
            )

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """ Ajout d'une ligne de prorata dans la facture générée """
        invoice_ids = super(SaleOrder, self).action_invoice_create(grouped=grouped, final=final)

        for order in self:
            if not order.of_prorata_percent and not order.of_retenue_garantie_pct:
                continue

            for invoice in order.invoice_ids:
                if invoice.id in invoice_ids:
                    break
            else:
                # Facture non trouvée ?
                continue

            # Calcul des totaux HT et TTC pour les lignes concernant le prorata et la retenue de garantie
            cur = order.currency_id
            round_globally = order.company_id.tax_calculation_rounding_method == 'round_globally'
            amount_untaxed = 0.0
            amount_tax = {}
            for line in order.order_line:
                if not line.product_uom_qty:
                    continue
                amount_untaxed += line.price_subtotal

                tax = line.tax_id
                amount_tax.setdefault(tax, 0.0)
                taxes = tax.compute_all(
                    line.price_subtotal, cur, 1.0, product=line.product_id, partner=order.partner_shipping_id)
                if round_globally:
                    price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    price_tax = taxes['total_included'] - taxes['total_excluded']
                amount_tax[tax] += price_tax
            amount_tax = sum(cur.round(val) for val in amount_tax.itervalues())

            invoice.of_add_retenue_line(order.of_retenue_garantie_pct, base_amount=amount_untaxed + amount_tax)
            invoice.of_add_prorata_line(order.of_prorata_percent, base_amount=amount_untaxed)
        return invoice_ids

    @api.multi
    def of_button_situation(self):
        self.ensure_one()
        wizard_obj = self.env['of.wizard.situation']
        product_situation_id = self.env['ir.values']\
            .get_default('sale.config.settings', 'of_product_situation_id_setting')
        if not product_situation_id:
            raise UserError(_(u"Vous devez définir l'Article de situation dans la configuration des ventes."))
        situation_data = {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'order_id': self.id,
            'line_ids': [(0, 0, {'order_line_id': line.id}) for line in self.order_line
                         if line.product_uom_qty or line.situation_ids],
        }
        wizard = wizard_obj.create(situation_data)

        action = {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.wizard.situation',
            'res_id': wizard.id,
            'target': 'current',
        }
        return action

    @api.multi
    def of_button_last_situation(self):
        self.ensure_one()
        wizard_obj = self.env['of.wizard.situation']
        product_situation_id = self.env['ir.values'].get_default(
            'sale.config.settings', 'of_product_situation_id_setting')
        if not product_situation_id:
            raise UserError(_(u"Vous devez définir l'article de situation dans la configuration des ventes."))
        situation_data = {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'order_id': self.id,
            'line_ids': [(0, 0, {'order_line_id': line.id}) for line in self.order_line
                         if line.product_uom_qty or line.situation_ids],
        }

        # On crée le wizard et on met toutes les lignes à 100 pour la dernière facture de situation
        wizard = wizard_obj.create(situation_data)
        for line in wizard.line_ids:
            line.sit_val_n = 100 - line.sit_val_prec
        wizard.button_make_invoice()

        # On crée la facture finale
        return self.action_invoice_create(final=True)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    situation_ids = fields.One2many(
        comodel_name='of.sale.order.line.situation', inverse_name='order_line_id', string=u"Lignes de situation")


class SaleOrderLineSituation(models.Model):
    _name = 'of.sale.order.line.situation'
    _order = 'order_id DESC, order_line_id DESC, situation'

    order_id = fields.Many2one(comodel_name='sale.order', related='order_line_id.order_id', readonly=True)
    order_line_id = fields.Many2one(
        comodel_name='sale.order.line', string=u"Ligne de commande", readonly=True, required=True, ondelete='cascade')
    situation = fields.Integer(string=u"Situation", required=True)
    value = fields.Float(string=u"Réalisation (%)")
    invoice_line_id = fields.Many2one(comodel_name='account.invoice.line', string=u"Ligne de facture", readonly=True)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def of_add_retenue_line(self, retenue_garantie_pct, sale_order=False, base_amount=False):
        self.ensure_one()
        if not retenue_garantie_pct:
            return
        if base_amount is False:
            base_amount = self.amount_total
        order_line_obj = self.env['sale.order.line']
        invoice_line_obj = self.env['account.invoice.line']

        product_retenue_id = self.env['ir.values'].get_default('sale.config.settings', 'of_product_retenue_id_setting')
        if not product_retenue_id:
            raise UserError(_(
                u"Vous devez renseigner un article de retenue de garantie dans la configuration des ventes"))
        product_retenue = self.env['product.product'].browse(product_retenue_id)

        # Normalement le compte devrait toujours être le 411700 et la taxe devrait toujours être à 0
        account = invoice_line_obj.get_invoice_line_account(
            'in_invoice', product_retenue, self.fiscal_position_id, self.company_id)
        taxes = self.company_id._of_filter_taxes(product_retenue.taxes_id)
        taxes = self.fiscal_position_id.map_tax(taxes, product_retenue, self.partner_id)
        amount = self.currency_id.round(base_amount * retenue_garantie_pct * -0.01)

        # --- Création de la ligne de commande si la commande est renseignée ---
        so_line = sale_order and order_line_obj.create({
            'name': "Retenue de garantie de %s%%" % (retenue_garantie_pct, ),
            'price_unit': amount,
            'product_uom_qty': 0.0,
            'order_id': sale_order.id,
            'discount': 0.0,
            'product_uom': product_retenue.uom_id.id,
            'product_id': product_retenue.id,
            'tax_id': [(6, 0, taxes._ids)],
        })

        inv_line = invoice_line_obj.create({
            'invoice_id': self.id,
            'name': "Retenue de garantie de %s%%" % (retenue_garantie_pct, ),
            'origin': self.origin,
            'account_id': account.id,
            'price_unit': amount,
            'quantity': 1.0,
            'discount': 0.0,
            'uom_id': product_retenue.uom_id.id,
            'product_id': product_retenue.id,
            'sale_line_ids': so_line and [(6, 0, [so_line.id])] or [],
            'invoice_line_tax_ids': [(6, 0, taxes._ids)],
            'account_analytic_id': sale_order and sale_order.project_id.id or False,
        })
        # Ces lignes sont là par sécurité, mais normalement inutiles car taxe à 0 sur la ligne.
        inv_line.onchange_tax_ids()
        self.compute_taxes()

    @api.multi
    def of_add_prorata_line(self, pct, sale_order=False, base_amount=False):
        """ Ajoute une ligne de prorata à la facture.
        L'article de prorata est défini dans la configuration de vente et détermine la taxe qui sera utilisée.
        Normalement il s'agit toujours d'une charge taxée à 20%.
        @param order: Commande associée à la facture, pour ajout d'une ligne de commande
        @param amount : Si False, le montant sera le total hors taxes de la facture
        """
        self.ensure_one()
        if not pct:
            return
        if base_amount is False:
            product_retenue_id = self.env['ir.values'].get_default(
                'sale.config.settings', 'of_product_retenue_id_setting')
            if product_retenue_id:
                # La retenue de garantie ne doit pas impacter le calcul du prorata
                lines = self.invoice_line_ids.filtered(lambda line: line.product_id.id != product_retenue_id)
                base_amount = sum(lines.mapped('price_subtotal'))
            else:
                base_amount = self.amount_untaxed
        if not base_amount:
            return
        order_line_obj = self.env['sale.order.line']
        invoice_line_obj = self.env['account.invoice.line']
        product_prorata_id = self.env['ir.values'].get_default('sale.config.settings', 'of_product_prorata_id_setting')
        if not product_prorata_id:
            raise UserError(_(u"Vous devez renseigner un article de prorata dans la configuration des ventes"))
        product_prorata = self.env['product.product'].browse(product_prorata_id)

        product_prorata_name = product_prorata.name_get()[0][1]
        if product_prorata.description_sale:
            product_prorata_name += '\n' + product_prorata.description_sale
        # Utilisation des comptes/taxes à l'achat et non à la vente
        taxes = self.company_id._of_filter_taxes(product_prorata.supplier_taxes_id)
        taxes = self.fiscal_position_id.map_tax(taxes, product_prorata, self.partner_id)

        # Calcul du montant de prorata
        amount = pct * base_amount * -0.01
        amount = self.currency_id.round(amount)

        # --- Création de la ligne de commande si la commande est renseignée ---
        so_line = sale_order and order_line_obj.create({
            'name': product_prorata_name,
            'price_unit': amount,
            'product_uom_qty': 0.0,
            'order_id': sale_order.id,
            'discount': 0.0,
            'product_uom': product_prorata.uom_id.id,
            'product_id': product_prorata.id,
            'tax_id': [(6, 0, taxes._ids)],
        })

        # --- Création de la ligne de facture ---
        account = invoice_line_obj.get_invoice_line_account(
            'in_invoice', product_prorata, self.fiscal_position_id, self.company_id)

        # Si le module of_account_tax est installé, on calcule le compte comptable en fonction des taxes
        if hasattr(taxes, 'map_account'):
            for tax in taxes:
                account = tax.map_account(account)

        inv_line = invoice_line_obj.create({
            'invoice_id': self.id,
            'name': product_prorata_name,
            'origin': self.origin,
            'account_id': account.id,
            'price_unit': amount,
            'quantity': 1.0,
            'discount': 0.0,
            'uom_id': product_prorata.uom_id.id,
            'product_id': product_prorata.id,
            'sale_line_ids': so_line and [(6, 0, [so_line.id])] or [],
            'invoice_line_tax_ids': [(6, 0, taxes._ids)],
            'account_analytic_id': sale_order and sale_order.project_id.id or False,
        })
        inv_line.onchange_tax_ids()
        self.compute_taxes()


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def get_locked_product_ids(self):
        locked_products = super(AccountInvoiceLine, self).get_locked_product_ids()
        locked_products += [
            self.env['ir.values'].get_default('sale.config.settings', 'of_product_prorata_id_setting'),
            self.env['ir.values'].get_default('sale.config.settings', 'of_product_situation_id_setting'),
            self.env['ir.values'].get_default('sale.config.settings', 'of_product_retenue_id_setting'),
        ]
        return locked_products


class Company(models.Model):
    _inherit = 'res.company'

    of_journal_situation_id = fields.Many2one(
        comodel_name='account.journal', compute='_compute_of_journal_situation_id', string=u"Journal de situation")

    @api.depends()
    def _compute_of_journal_situation_id(self):
        journal_obj = self.env['account.journal']
        for company in self:
            journal = journal_obj.search([('company_id', '=', company.id),
                                          ('type', '=', 'sale'),
                                          ('name', 'like', 'situation')], limit=1)
            if not journal:
                journal = journal_obj.search([('company_id', '=', company.id),
                                              ('type', '=', 'sale')], limit=1)
            company.of_journal_situation_id = journal


class OFSaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    of_product_prorata_id_setting = fields.Many2one(
        comodel_name='product.product',
        string=u"(OF) Article de prorata",
        help=u"Article utilisé pour le compte de prorata")

    of_product_situation_id_setting = fields.Many2one(
        comodel_name='product.product',
        string=u"(OF) Article de situation",
        help=u"Article utilisé pour les factures de situation")

    of_product_retenue_id_setting = fields.Many2one(
        comodel_name='product.product',
        string=u"(OF) Article de retenue de garantie",
        help=u"Article utilisé pour la retenue de garantie")

    @api.multi
    def set_of_product_prorata_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_product_prorata_id_setting', self.of_product_prorata_id_setting.id)

    @api.multi
    def set_of_product_situation_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_product_situation_id_setting', self.of_product_situation_id_setting.id)

    @api.multi
    def set_of_product_retenue_id_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_product_retenue_id_setting', self.of_product_retenue_id_setting.id)
