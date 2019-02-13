# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

fo = {'daily': 'Jour(s)',
      'weekly': 'Semaine(s)',
      'monthly': 'Mois',
      'monthlylastday': 'Month(s) last day',
      'yearly': u'Année(s)'}

class OfAccountInvoice(models.Model):
    _inherit = "account.invoice"

    of_contract_id = fields.Many2one('of.contract', string="(OF) Contrat")

class OfAccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    of_contract_id = fields.Many2one('of.contract', string="(OF) Contrat")
    of_service_id = fields.Many2one('of.service', string="(OF) Service")

class OfContract(models.Model):
    _name = "of.contract"

    invoice_count = fields.Integer(string='# of Invoices', compute='_get_invoiced', readonly=True)
    name = fields.Char(
        required=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Client",
        required=True,
    )
    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string='Liste de prix',
    )
    service_ids = fields.One2many(
        comodel_name='of.service',
        inverse_name='contract_id',
        string='Services',
    )
    recurring_rule_type = fields.Selection(
        [('daily', 'Jour(s)'),
         ('weekly', 'Semaine(s)'),
         ('monthly', 'Mois'),
         ('monthlylastday', 'Month(s) last day'),
         ('yearly', u'Année(s)'),
         ],
        default='monthly',
        string=u'Réccurence',
        help="Specify Interval for automatic invoice generation.",
        required=True
    )
    recurring_invoicing_type = fields.Selection(
        [('contract', u'Récurrence du contrat'),
         ('services', u'Récurrence des services'),
         ],
        default='contract',
        string='Type de facturation',
        help="Specify if process date is 'from' or 'to' invoicing date",
    )
    recurring_interval = fields.Integer(
        default=1,
        string=u'Répéter chaque',
        help="Repeat every (Days/Week/Month/Year)",
        required=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        default=lambda s: s._default_journal(),
        domain="[('type', '=', 'sale'),('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(
        'res.company',
        string=u'Société',
        required=True,
        default=lambda self: self.env.user.company_id,
    )
    date_start = fields.Date(
        string=u'Date début',
        default=fields.Date.context_today,
    )
    date_end = fields.Date(
        string='Date fin',
        index=True,
    )
    recurring_next_date = fields.Date(
        default=fields.Date.context_today,
        copy=False,
        string='Date de la prochaine facture',
        compute="_compute_next_date",
    )
    fiscal_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale")
    next_subtotal = fields.Monetary(string="Prochain montant HT", compute='_compute_next_total', currency_field='company_currency_id')
    next_taxes = fields.Monetary(string="Taxes ", compute='_compute_next_total', currency_field='company_currency_id')
    next_total = fields.Monetary(string="Prochain Total", compute='_compute_next_total', currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True)

    last_invoicing_date = fields.Date(string=u"Date de dernière facturation", copy=False)

    @api.depends('recurring_invoicing_type', 'last_invoicing_date', 'date_start')
    def _compute_next_date(self):
        for contract in self:
            if contract.recurring_invoicing_type == 'contract':
                if contract.last_invoicing_date:
                    contract.recurring_next_date = fields.Date.to_string(fields.Date.from_string(contract.last_invoicing_date) + self.get_relative_delta(
                        contract.recurring_rule_type, contract.recurring_interval))
                else:
                    contract.recurring_next_date = fields.Date.to_string(datetime.today())
            else:
                lines = contract.service_ids.filtered(lambda l: l.product_id)
                if lines:
                    date_next = fields.Date.from_string(lines[0].next_date)
                    for line in lines:
                        date = fields.Date.from_string(line.next_date)
                        if date and date < date_next:
                            date_next = date
                    contract.recurring_next_date = date_next and fields.Date.to_string(date_next) or fields.Date.to_string(datetime.today())
                else:
                    contract.recurring_next_date = contract.date_start

    @api.depends('service_ids', 'recurring_rule_type', 'recurring_interval', 'fiscal_position_id')
    def _compute_next_total(self):
        for contract in self:
            next_date = fields.Date.from_string(contract.recurring_next_date) or self._context.get('recurring_next_date') and fields.Date.from_string(self.context.get('recurring_next_date')) or fields.Date.from_string(fields.Date.today())
            lines = contract.service_ids.filtered(lambda l: l.product_id and (fields.Date.from_string(l.next_date) or fields.Date.from_string(fields.Date.today())) <= next_date)
            subtotal = sum(lines.mapped('price_subtotal'))
            contract.next_subtotal = subtotal
            if contract.fiscal_position_id.default_tax_ids:
                tax_amount = contract.fiscal_position_id.default_tax_ids[0].amount / 100.0
                total_tax = sum([line.price_subtotal * tax_amount for line in lines])
                contract.next_taxes = total_tax
            else:
                tax = self.env['ir.values'].get_default('acconut.config.settings', 'default_sale_tax_id')
                if tax:
                    tax_amount = tax.amount / 100
                else:
                    tax_amount = 0
                total_tax = sum([line.price_subtotal * tax_amount for line in lines])
                contract.next_taxes = total_tax
            contract.next_total = total_tax + subtotal

    @api.model
    def _insert_markers(self, line, date_start, next_date, date_format):
        contract = line.contract_id
        if contract.recurring_invoicing_type == 'pre-paid':
            date_from = date_start
            date_to = next_date - relativedelta(days=1)
        else:
            date_from = (date_start -
                         self.get_relative_delta(contract.recurring_rule_type,
                                                 contract.recurring_interval) +
                         relativedelta(days=1))
            date_to = date_start
        name = line.name or ""
        name = name.replace('#START#', date_from.strftime(date_format))
        name = name.replace('#END#', date_to.strftime(date_format))
        return name

    @api.model
    def get_relative_delta(self, recurring_rule_type, interval):
        if recurring_rule_type == 'daily':
            return relativedelta(days=interval)
        elif recurring_rule_type == 'weekly':
            return relativedelta(weeks=interval)
        elif recurring_rule_type == 'monthly':
            return relativedelta(months=interval)
        elif recurring_rule_type == 'monthlylastday':
            return relativedelta(months=interval, day=31)
        else:
            return relativedelta(years=interval)

    @api.model
    def _default_journal(self):
        company_id = self.env.context.get(
            'company_id', self.env.user.company_id.id)
        domain = [
            ('type', '=', 'sale'),
            ('company_id', '=', company_id)]
        return self.env['account.journal'].search(domain, limit=1)

    @api.onchange('partner_id')
    def onchange_partner(self):
        self.fiscal_position_id = self.partner_id.property_account_position_id

    def get_quantity(self, line, old_date):
        if self.recurring_invoicing_type == 'services':
            return line.quantity
        else:
            begin = fields.Date.from_string(line.first_invoicing) or fields.Date.from_string(self.recurring_next_date)
            quant = sum(self.env['account.invoice.line'].search([('of_service_id', '=', line.id)]).mapped('quantity'))
            to_invoice_quant = line.quantity
            while (begin < old_date):
                begin += self.get_relative_delta(line.frequency_type, line.frequency)
                to_invoice_quant += line.quantity
            if begin > old_date:
                to_invoice_quant -= 1
            return to_invoice_quant - quant

    @api.model
    def _prepare_invoice_line(self, line, invoice_id, old_date):
        invoice_line = self.env['account.invoice.line'].new({
            'invoice_id': invoice_id,
            'product_id': line.product_id.id,
            'quantity': self.get_quantity(line, old_date),
            'uom_id': line.uom_id.id,
            'discount': line.discount,
            'of_service_id': line.id,
        })
        # Get other invoice line values from product onchange
        invoice_line._onchange_product_id()
        invoice_line_vals = invoice_line._convert_to_write(invoice_line._cache)
        # Insert markers
        name = line.name
        contract = line.contract_id
        if 'old_date' in self.env.context and 'next_date' in self.env.context:
            lang_obj = self.env['res.lang']
            lang = lang_obj.search(
                [('code', '=', contract.partner_id.lang)])
            date_format = lang.date_format or '%m/%d/%Y'
            name = self._insert_markers(
                line, self.env.context['old_date'],
                self.env.context['next_date'], date_format)
        invoice_line_vals.update({
            'name': name,
            'of_contract_id': contract.id,
            'price_unit': line.price_unit,
        })
        return invoice_line_vals

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError(
                u"Vous devez d'abord sélectionner un client pour le contrat %s!" %
                self.name)
        journal = self.journal_id or self.env['account.journal'].search(
            [('type', '=', 'sale'),
             ('company_id', '=', self.company_id.id)],
            limit=1)
        if not journal:
            raise ValidationError(
                u"Veuillez définir un journal de vente pour votre société '%s'." %
                (self.company_id.name or '',))
        currency = (
            self.pricelist_id.currency_id or
            self.partner_id.property_product_pricelist.currency_id or
            self.company_id.currency_id
        )
        invoice = self.env['account.invoice'].new({
            'reference': self.name,
            'type': 'out_invoice',
            'partner_id': self.partner_id.address_get(
                ['invoice'])['invoice'],
            'currency_id': currency.id,
            'journal_id': journal.id,
            'date_invoice': self.recurring_next_date,
            'origin': self.name,
            'company_id': self.company_id.id,
            'of_contract_id': self.id,
            'user_id': self.partner_id.user_id.id,
            'fiscal_position_id': self.fiscal_position_id.id,
        })
        # Get other invoice values from partner onchange
        invoice._onchange_partner_id()
        invoice.fiscal_position_id = self.fiscal_position_id.id
        return invoice._convert_to_write(invoice._cache)

    @api.multi
    def _create_invoice(self, old_date):
        self.ensure_one()
        invoice_vals = self._prepare_invoice()
        invoice = self.env['account.invoice'].create(invoice_vals)
        for line in self.service_ids.filtered('product_id').filtered(lambda l: fields.Date.from_string(l.next_date) <= old_date):
            invoice_line_vals = self._prepare_invoice_line(line, invoice.id, old_date)
            self.env['account.invoice.line'].create(invoice_line_vals)
            if line.first_invoicing:
                line.write({'previous_date': fields.Date.to_string(old_date)})
            else:
                line.write({'previous_date': fields.Date.to_string(old_date), 'first_invoicing': fields.Date.to_string(old_date)})
        invoice.compute_taxes()
        return invoice

    @api.multi
    def recurring_create_invoice(self):
        """Create invoices from contracts
        :return: invoices created
        """
        invoices = self.env['account.invoice']
        for contract in self:
            if len(contract.service_ids) == 0:
                raise UserError(u"Impossible de créer une facture car le contrat n'a aucune ligne facturable pour le contrat %s : %s." % (contract.name, contract.partner_id.name))
            ref_date = contract.recurring_next_date
            if (contract.date_start > ref_date or
                    contract.date_end and contract.date_end < ref_date):
                raise ValidationError(
                    u"Vous devez revoir les dates de début et de fin pour le contrat %s : %s." %
                    (contract.name, contract.partner_id.name)
                )
            old_date = fields.Date.from_string(ref_date)
            new_date = old_date + self.get_relative_delta(
                contract.recurring_rule_type, contract.recurring_interval)
            ctx = self.env.context.copy()
            ctx.update({
                'old_date': old_date,
                'next_date': new_date,
                # Force company for correct evaluation of domain access rules
                'force_company': contract.company_id.id,
            })
            # Re-read contract with correct company
            invoices |= contract.with_context(ctx)._create_invoice(old_date)
            contract.write({
                'last_invoicing_date': fields.Date.to_string(old_date)
            })
        return invoices

    @api.depends('partner_id')
    def _get_invoiced(self):
        for contract in self:
            contract.invoice_count = len(self.env['account.invoice'].search([('of_contract_id', '=', contract.id)]))

    @api.multi
    def action_view_invoice(self):
        invoices = self.env['account.invoice'].search([('of_contract_id', '=', self.id)])
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

class OfService(models.Model):
    _inherit= "of.service"

    tache_id = fields.Many2one('of.planning.tache', string=u'Tâche', required=False)
    name = fields.Char(u"Libellé", related='tache_id.name', store=False)

    mois_ids = fields.Many2many('of.mois', 'service_mois', 'service_id', 'mois_id', string='Mois', required=False)
    jour_ids = fields.Many2many('of.jours', 'service_jours', 'service_id', 'jour_id', string='Jours', required=False)

    note = fields.Text('Notes')
    date_next = fields.Date('Prochaine intervention', help=u"Date à partir de laquelle programmer la prochaine intervention", required=False)
    date_fin = fields.Date(u"Date d'échéance")

    # Partner-related fields
    partner_zip = fields.Char('Code Postal', size=24, related='address_id.zip')
    partner_city = fields.Char('Ville', related='address_id.city')

    state = fields.Selection([
        ('progress', 'En cours'),
        ('cancel', u'Annulé'),
        ], u'État')
    active = fields.Boolean(string="Active", default=True)

    planning_ids = fields.One2many('of.planning.intervention', compute='_get_planning_ids', string="Interventions")
    date_last = fields.Date(u'Dernière intervention', compute='_get_planning_ids', search='_search_last_date', help=u"Date de la dernière intervention")

    # Champs de recherche
    date_fin_min = fields.Date(string=u"Date échéance min", compute='lambda *a, **k:{}')
    date_fin_max = fields.Date(string=u"Date échéance max", compute='lambda *a, **k:{}')
    date_controle = fields.Date(string=u"Date de contrôle", compute='lambda *a, **k:{}')

    # Couleur de contrôle
    color = fields.Char(compute='_compute_color', string='Couleur', store=False)

    intervention_model_id = fields.Many2one('of.planning.intervention.model', string=u"Modèle d'intervention")
    contract_id = fields.Many2one('of.contract', string=u"Contrat")
    frequency = fields.Integer(string=u"Fréquence", default=1)
    frequency_type = fields.Selection([('daily', 'Jour(s)'),
         ('weekly', 'Semaine(s)'),
         ('monthly', 'Mois'),
         ('monthlylastday', 'Month(s) last day'),
         ('yearly', u'Année(s)'),
         ], default='monthly')
    first_invoicing = fields.Date(string=u"Première facturation")
    previous_date = fields.Date(string=u"Dernière facturation")
    next_date = fields.Date(string="Prochaine facturation", compute="_compute_next_date", store=False)

    @api.onchange('intervention_model_id')
    def onchange_intervention_model(self):
        if self.intervention_model_id.tache_id:
            self.tache_id = self.intervention_model_id.tache_id

    @api.model
    def get_relative_delta(self, recurring_rule_type, interval):
        if recurring_rule_type == 'daily':
            return relativedelta(days=interval)
        elif recurring_rule_type == 'weekly':
            return relativedelta(weeks=interval)
        elif recurring_rule_type == 'monthly':
            return relativedelta(months=interval)
        elif recurring_rule_type == 'monthlylastday':
            return relativedelta(months=interval, day=31)
        else:
            return relativedelta(years=interval)

    @api.depends('previous_date', 'contract_id', 'product_id')
    def _compute_next_date(self):
        for line in self:
            if line.previous_date:
                line.next_date = fields.Date.to_string(fields.Date.from_string(line.previous_date) + self.get_relative_delta(line.frequency_type, line.frequency))
            else:
                line.next_date = line.contract_id.recurring_next_date or line.contract_id.date_start or fields.Date.to_string(datetime.today())

    product_id = fields.Many2one(
        'product.product',
        string='Article',
    )
    product_name = fields.Text(
        string='Description',
    )
    quantity = fields.Float(
        default=1.0,
    )
    uom_id = fields.Many2one(
        'product.uom',
        string=u'Unité de mesure',
    )
    automatic_price = fields.Boolean(
        string="Prix automatique",
        help="If this is marked, the price will be obtained automatically "
             "applying the pricelist to the product. If not, you will be "
             "able to introduce a manual price",
    )
    specific_price = fields.Float(
        string=u'Prix spécifique',
    )
    price_unit = fields.Float(
        string='Prix unitaire',
        compute="_compute_price_unit",
        inverse="_inverse_price_unit",
    )
    price_subtotal = fields.Float(
        compute='_compute_price_subtotal',
        digits=dp.get_precision('Account'),
        string='Sous-total',
    )
    discount = fields.Float(
        string='Remise (%)',
        digits=dp.get_precision('Discount'),
        help='Discount that is applied in generated invoices.'
             ' It should be less or equal to 100',
    )
    sequence = fields.Integer(
        string=u"Séquence",
        default=10,
        help="Sequence of the contract line when displaying contracts",
    )

    @api.depends(
        'automatic_price',
        'specific_price',
        'product_id',
        'quantity',
        'contract_id.pricelist_id',
        'contract_id.partner_id',
    )
    def _compute_price_unit(self):
        """Get the specific price if no auto-price, and the price obtained
        from the pricelist otherwise.
        """
        for line in self:
            if line.automatic_price:
                product = line.product_id.with_context(
                    quantity=line.quantity,
                    pricelist=line.contract_id.pricelist_id and line.contract_id.pricelist_id.id or line.address_id.property_product_pricelist.id,
                    partner=line.partner_id.id,
                    date=line.env.context.get('old_date', fields.Date.today()),
                )
                line.price_unit = product.lst_price
            else:
                line.price_unit = line.specific_price

    def _inverse_price_unit(self):
        """Store the specific price in the no auto-price records."""
        for line in self.filtered(lambda x: not x.automatic_price):
            line.specific_price = self.price_unit

    @api.multi
    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_price_subtotal(self):
        for line in self:
            subtotal = line.quantity * line.price_unit
            discount = line.discount / 100
            subtotal *= 1 - discount
            if line.contract_id.pricelist_id or line.address_id.property_product_pricelist:
                cur = line.contract_id.pricelist_id.currency_id or line.address_id.property_product_pricelist.currency_id
                line.price_subtotal = cur.round(subtotal)
            else:
                line.price_subtotal = subtotal

    @api.multi
    @api.constrains('discount')
    def _check_discount(self):
        for line in self:
            if line.discount > 100:
                raise ValidationError(
                    _("Discount should be less or equal to 100"))

    @api.multi
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return {'domain': {'uom_id': []}}

        vals = {}
        domain = {'uom_id': [
            ('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not self.uom_id or (self.product_id.uom_id.category_id.id !=
                               self.uom_id.category_id.id):
            vals['uom_id'] = self.product_id.uom_id

        date = (
            self.contract_id.recurring_next_date or
            fields.Date.today()
        )
        partner = self.address_id or self.env.user.partner_id

        product = self.product_id.with_context(
            lang=partner.lang,
            partner=partner.id,
            quantity=self.quantity,
            date=date,
            pricelist=self.contract_id.pricelist_id and self.contract_id.pricelist_id.id or partner.property_product_pricelist,
            uom=self.uom_id.id
        )

        name = product.name_get()[0][1]
        if product.description_sale:
            name += '\n' + product.description_sale
        vals['product_name'] = name

        vals['price_unit'] = product.lst_price
        self.update(vals)
        return {'domain': domain}

