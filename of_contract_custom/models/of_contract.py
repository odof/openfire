# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.addons.of_utils.models.of_utils import format_date, se_chevauchent
from odoo.tools.safe_eval import safe_eval


class OfDocumentsJoints(models.AbstractModel):
    _inherit = 'of.documents.joints'

    @api.model
    def _allowed_reports(self):
        res = super(OfDocumentsJoints, self)._allowed_reports()
        res.update({'of_contract_custom.report_contract': 'of.contract'})
        return res


class OfContractRecurringInvoicingPayment(models.Model):
    _name = 'of.contract.recurring.invoicing.payment'

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string=u"Libellé")

    @api.multi
    def write(self, vals):
        if (len(self) > 1 and 'code' in vals) or (len(self) == 1 and vals.get('code', self.code) != self.code):
            raise UserError("Impossible de modifier le code du type de facturation")
        if 'code' in vals:
            del vals['code']
        return super(OfContractRecurringInvoicingPayment, self).write(vals)


class OfContract(models.Model):
    _name = "of.contract"
    _inherit = ['mail.thread', 'of.form.readonly', 'of.documents.joints']

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        cr.execute(
            "SELECT * FROM information_schema.columns "
            "WHERE table_name = '%s' AND column_name = 'contract_type'" % (self._table,))
        exist1 = bool(cr.fetchall())
        cr.execute(
            "SELECT * FROM information_schema.columns "
            "WHERE table_name = '%s' AND column_name = 'type'" % (self._table,))
        exist2 = bool(cr.fetchall())
        res = super(OfContract, self)._auto_init()
        if not exist1 and exist2:
            cr.execute("UPDATE %s "
                       "SET contract_type = 'advanced'" % (self._table, ))
            self.env['ir.values'].sudo().set_default(
                'of.intervention.settings', 'of_contract', True)
        return res

    active = fields.Boolean(default=True)
    invoice_ids = fields.One2many(comodel_name='account.invoice', inverse_name='of_contract_id', string="Factures")
    invoice_count = fields.Integer(string='Nombre de factures', compute='_get_invoice_count', readonly=True)
    name = fields.Char(string="Nom", required=False, compute="_compute_name", store=True)
    reference = fields.Char(string=u"Référence", required=True)
    partner_id = fields.Many2one("res.partner", string="Client payeur", required=True)
    department_id = fields.Many2one(
        'res.country.department', related='partner_id.department_id', string=u"Département", readonly=True, store=True)
    category_ids = fields.Many2many(
        'res.partner.category', related="partner_id.category_id", string=u"Étiquettes client")
    pricelist_id = fields.Many2one('product.pricelist', string='Liste de prix')
    line_ids = fields.One2many('of.contract.line', 'contract_id', string='Lignes de contrat')
    line_ids_rel = fields.One2many(related='line_ids', string='Lignes de contrat')
    recurring_rule_type = fields.Selection([
        ('date', u'À la prestation'),
        ('month', 'Mensuelle'),
        ('trimester', u'Trimestrielle'),  # Tout les 3 mois
        ('semester', u'Semestrielle'),  # 2 fois par ans
        ('year', u'Annuelle'),
        ], string=u"Fréquence de facturation", help="Intervalle de temps entre chaque facturation",
        required=True
    )
    recurring_invoicing_payment_id = fields.Many2one(
        'of.contract.recurring.invoicing.payment', string="Type de facturation", required=True)
    journal_id = fields.Many2one(
        'account.journal', string='Journal', default=lambda s: s._default_journal(),
        domain="[('type', '=', 'sale'),('company_id', '=', company_id)]")
    account_analytic_id = fields.Many2one('account.analytic.account', string=u"Compte analytique")
    company_id = fields.Many2one(
        'res.company', string=u'Société', required=True,
        default=lambda self: self.env.context.get('company_id', self.env.user.company_id.id))
    date_souscription = fields.Date(string=u'Date de souscription', default=fields.Date.context_today, required=True)
    date_start = fields.Date(string=u'Date de début', default=fields.Date.context_today, required=True)
    period = fields.Integer(string=u"Période d'activité", required=True, default=12, readonly=True)
    date_end = fields.Date(string='Date de fin')
    recurring_next_date = fields.Date(string='Date de la prochaine facture', compute="_compute_next_date", store=True)
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string="Position fiscale", domain="[('company_id', '=', company_id)]")
    next_subtotal = fields.Monetary(
        string="Prochain montant HT", compute='_compute_next_total', currency_field='company_currency_id', store=True)
    next_taxes = fields.Monetary(
        string="Taxes ", compute='_compute_next_total', currency_field='company_currency_id', store=True)
    next_total = fields.Monetary(
        string="Prochain Total", compute='_compute_next_total', currency_field='company_currency_id', store=True)
    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string="Company Currency", readonly=True)

    last_invoicing_date = fields.Date(
        string=u"Date de dernière facturation", copy=False, compute="_compute_last_invoicing_date", store=True)
    intervention_count = fields.Integer(compute="_compute_intervention_count")
    intervention_ids = fields.One2many(
        comodel_name='of.planning.intervention', inverse_name='contract_id', string="RDV(s) d'intervention")
    is_invoiceable = fields.Boolean(compute="_compute_is_invoiceable", store=True)
    current_period_id = fields.Many2one(
        comodel_name='of.contract.period', string=u"Période du contrat",
        compute="_compute_current_period_id", store=True)
    type = fields.Selection([
            (0, 'Nouveau contrat'),
            (1, 'Renouvellement'),
        ], string="Type de contrat", default=0
    )
    contract_type = fields.Selection([
        ('simple', u'Simple'),
        ('advanced', u'Avancé'),
        ], string="Type de contrat", default='simple'
    )
    state = fields.Selection([
        ('upcoming', u'À venir'),
        ('in_progress', 'En cours'),
        ('inactive', 'Inactif'),
    ], string=u"État", compute="_compute_state")
    renewal = fields.Boolean(string="Renouvellement automatique", default=True)
    commentaires = fields.Text(string="Commentaires")
    use_index = fields.Boolean(string="Indexer")
    period_ids = fields.One2many(
        comodel_name='of.contract.period', inverse_name='contract_id', string=u"Périodes")
    revision = fields.Selection([
        ('none', 'Aucune'),
        ('last_day', 'Dernier jour du contrat'),
        ], string=u"Période de révision", default='last_day')
    service_ids = fields.One2many(
        comodel_name='of.service', compute="_compute_service_ids", string="Demandes d'intervention")
    grouped = fields.Boolean(string="Regrouper la facturation")
    payment_term_id = fields.Many2one('account.payment.term', string=u'Conditions de règlement')
    date_indexed = fields.Date(string=u"Dernière indexation", compute="_compute_date_indexed", store=True)
    validated = fields.Boolean(string=u"Au moins une ligne validée", compute='_compute_validated')
    automatic_sequence = fields.Boolean(
        string=u"Séquence automatique", compute='_compute_automatic_sequence',
        default=lambda c: c._default_automatic_sequence())
    intervention_sites = fields.Char(string=u"Sites d'intervention", compute='_compute_intervention_sites')

    @api.model
    def _default_journal(self):
        company_id = self.env.context.get(
            'company_id', self.env.user.company_id.id)
        domain = [
            ('type', '=', 'sale'),
            ('company_id', '=', company_id)]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _default_automatic_sequence(self):
        return self.env.user.has_group('of_contract_custom.group_contract_automatic_sequence')

    @api.depends('reference', 'partner_id')
    def _compute_name(self):
        """ Compute du champ name en fonction de la référence et du partenaire """
        for contrat in self:
            contrat.name = "%s - %s" % (contrat.reference, contrat.partner_id.name)

    @api.depends('line_ids', 'line_ids.intervention_ids')
    def _compute_intervention_count(self):
        """ Calcule du nombre de RDVs d'interventions liées au contrat (somme des RDV des lignes de contrat) """
        for contrat in self:
            count = 0
            for service in contrat.line_ids:
                count += len(service.intervention_ids)
            contrat.intervention_count = count

    @api.depends('line_ids', 'line_ids.is_invoiceable', 'line_ids.next_date', 'recurring_next_date')
    def _compute_is_invoiceable(self):
        """ Contrat peut être facturé si au moins une ligne est facturable """
        for contrat in self:
            old_date = fields.Date.from_string(contrat.recurring_next_date)
            lines = contrat.line_ids.filtered('is_invoiceable').filtered(
                    lambda l: l.next_date and fields.Date.from_string(l.next_date) <= old_date)
            contrat.is_invoiceable = lines and True or False

    @api.depends('recurring_next_date', 'date_end', 'date_start', 'period_ids')
    def _compute_current_period_id(self):
        """ Changement de période en fonction des différentes dates """
        for contract in self:
            if not contract.period_ids:
                continue
            if contract.recurring_next_date:
                ref_date = contract.recurring_next_date
            elif contract.last_invoicing_date and contract.date_end:
                ref_date = contract.date_end
            else:
                ref_date = contract.date_start
            contract.current_period_id = contract.period_ids.filtered(lambda p: p.date_start <= ref_date <= p.date_end)

    @api.depends()
    def _compute_state(self):
        """ Calcul de l'état du contrat en fonction de la date du jour, se recalcul quand le champ est affiché """
        today = fields.Date.today()
        for contract in self:
            if contract.date_start > today:
                contract.state = 'upcoming'
            elif contract.date_end and contract.date_end < today:
                contract.state = 'inactive'
            else:
                contract.state = 'in_progress'

    @api.depends('line_ids', 'line_ids.next_date')
    def _compute_next_date(self):
        """ Calcul de la date de prochaine facturation """
        for contract in self:
            if not contract.line_ids:
                continue
            next_date = contract.line_ids.filtered('next_date')
            if not next_date:
                continue
            contract.recurring_next_date = next_date.sorted('next_date')[0].next_date

    @api.depends('line_ids',
                 'line_ids.next_date',
                 'line_ids.amount_subtotal',
                 'line_ids.amount_taxes',
                 'line_ids.amount_total',
                 'line_ids.is_invoiceable',
                 'recurring_rule_type',
                 'fiscal_position_id',
                 'recurring_next_date')
    def _compute_next_total(self):
        """ Calcul le montant total de la prochaine facture
        """
        for contract in self:
            lines = contract.line_ids.filtered(lambda l: l.is_invoiceable and
                                                         l.next_date == contract.recurring_next_date)
            c_subtotal = 0
            c_total_tax = 0
            for line in lines:
                c_subtotal += line.amount_subtotal
                c_total_tax += line.amount_taxes
            contract.next_taxes = round(c_total_tax, 2)
            contract.next_subtotal = round(c_subtotal, 2)
            contract.next_total = c_total_tax + c_subtotal

    @api.depends('line_ids',
                 'line_ids.invoice_line_ids',
                 'line_ids.invoice_line_ids.invoice_id',
                 'line_ids.invoice_line_ids.invoice_id.state')
    def _compute_last_invoicing_date(self):
        """ Récupération de la dernière date de facturation """
        for contract in self:
            # en cas d'avoir, la facture est déliée des lignes de contrat mais pas du contrat.
            # on passe donc par les lignes de contrat pour connaitre la facture actuelle
            invoices = contract.line_ids.mapped('invoice_line_ids').mapped('invoice_id')\
                                        .filtered(lambda i: i.state in ['confirm', 'paid'])
            if invoices:
                contract.last_invoicing_date = invoices[0].date_invoice

    @api.depends('line_ids', 'line_ids.service_ids')
    def _compute_service_ids(self):
        """ Récupération des demandes d'intervention liées aux différentes lignes de contrat """
        for contract in self:
            contract.service_ids = contract.line_ids.mapped('service_ids')

    @api.depends('line_ids', 'line_ids.address_id')
    def _compute_intervention_sites(self):
        """ Récupération des sites d'intervention liés aux différentes lignes de contrat """
        for contract in self:
            contract.intervention_sites = ', '.join(
                contract.line_ids.mapped('address_id').mapped(lambda x: x.name or x.display_name))

    @api.depends('invoice_ids')
    def _get_invoice_count(self):
        """ Calcul du nombre de factures liées au contrat """
        for contract in self:
            contract.invoice_count = len(contract.invoice_ids)

    @api.depends('line_ids', 'line_ids.date_indexed')
    def _compute_date_indexed(self):
        for contract in self:
            lines = contract.line_ids.filtered('date_indexed').sorted('date_indexed')
            if lines:
                contract.date_indexed = lines[-1].date_indexed
            pass

    @api.depends('line_ids', 'line_ids.state')
    def _compute_validated(self):
        for contract in self:
            contract.validated = bool(contract.line_ids.filtered(lambda l: l.state == 'validated'))

    def _compute_automatic_sequence(self):
        has_group = self.env.user.has_group('of_contract_custom.group_contract_automatic_sequence')
        for contract in self:
            if has_group:
                contract.automatic_sequence = True
            else:
                contract.automatic_sequence = False

    @api.onchange('renewal')
    def _onchange_renewal(self):
        """ Si à renouveler alors pas de date de fin, autrement pré-remplissage de la date de fin (en fonction de la
            période courante) """
        if self.renewal:
            self.date_end = False
        if not self.renewal:
            if self.current_period_id:
                self.date_end = self.current_period_id.date_end
            elif self.date_start:
                date = fields.Date.from_string(self.date_start)
                end_date = date + relativedelta(years=1, day=1, month=1) - relativedelta(days=1)
                self.date_end = fields.Date.to_string(end_date)

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start:
            if not self.renewal:
                date = fields.Date.from_string(self.date_start)
                end_date = date + relativedelta(years=1, days=-1)
                self.date_end = fields.Date.to_string(end_date)

    @api.onchange('partner_id')
    def onchange_partner(self):
        """ Prend la position fiscale renseignée sur le client """
        self.fiscal_position_id = self.partner_id.property_account_position_id

    @api.onchange('recurring_rule_type')
    def _onchange_recurring_rule_type(self):
        self.ensure_one()
        if self.recurring_rule_type == 'date':
            if self.recurring_invoicing_payment_id.code not in ('date', 'post-paid'):
                self.recurring_invoicing_payment_id = False
        elif self.recurring_rule_type:
            if self.recurring_invoicing_payment_id.code not in ('pre-paid', 'post-paid'):
                self.recurring_invoicing_payment_id = False

    @api.onchange('contract_type')
    def _onchange_contract_type(self):
        if self.contract_type == 'simple':
            self.grouped = True
            self.revision = 'none'

    @api.model
    def create(self, vals):
        if self.env.user.has_group('of_contract_custom.group_contract_automatic_sequence'):
            sequence = self.env.ref('of_contract_custom.of_contract_custom_seq')
            vals['reference'] = sequence.next_by_id()
        res = super(OfContract, self).create(vals)
        if res.account_analytic_id:
            product_lines = res.line_ids.mapped('contract_product_ids')\
                .filtered(lambda p: not p.account_analytic_id)
            product_lines.write({'account_analytic_id': res.account_analytic_id.id})
        # Générer les périodes lors de la création
        res._generate_periods()
        return res

    @api.multi
    def write(self, vals):
        # on retire date_end car l'attribut readonly fait qu'on le vide mais cette information n'est pas renvoyée
        if 'renewal' in vals and vals.get('renewal'):
            vals['date_end'] = False
        res = super(OfContract, self).write(vals)
        if vals.get('account_analytic_id'):
            product_lines = self.mapped('line_ids').mapped('contract_product_ids')\
                .filtered(lambda p: not p.account_analytic_id)
            product_lines.write({'account_analytic_id': vals['account_analytic_id']})
        if 'date_start' in vals:
            self.mapped('period_ids').sudo().unlink()
            for contract in self:
                contract._generate_periods()
        return res

    @api.multi
    def _write(self, vals):
        # Passer le contrat en type renouvellement si la période change
        if 'current_period_id' in vals:
            cr = self.env.cr
            cr.execute("SELECT current_period_id FROM of_contract WHERE id = %s", (self.id,))
            current_period_id = cr.fetchone()[0]  # is either (None,) or (id,)
            if current_period_id and vals.get('current_period_id', current_period_id) != current_period_id:
                vals['type'] = 1
        # Générer la nouvelle période si elle n'existe pas
        if 'recurring_next_date' in vals and vals.get('recurring_next_date'):
            next_date = vals.get('recurring_next_date')
            for contract in self:
                if contract.period_ids and not contract.period_ids.filtered(lambda p: p.date_start <= next_date <= p.date_end):
                    last_period = contract.period_ids[-1]
                    contract._generate_periods(date_start=fields.Date.to_string(
                            fields.Date.from_string(last_period.date_start) + relativedelta(months=contract.period)))
        res = super(OfContract, self)._write(vals)
        return res

    @api.multi
    def _generate_periods(self, date_start=False):
        self.ensure_one()
        period_obj = self.env['of.contract.period']
        date_start = date_start or self.date_start
        max_date = fields.Date.from_string(fields.Date.today()) + relativedelta(years=11, month=1, day=1)
        numbers = self.period_ids.mapped('number')
        base = numbers and max(numbers) or 1
        ds = fields.Date.from_string(date_start)
        if ds >= max_date:
            return
        for i in xrange(base, base+10):
            date_end = ds + relativedelta(months=self.period, days=-1)
            date_start = fields.Date.to_string(ds)
            date_end_str = fields.Date.to_string(date_end)
            # if par sécurité, on devrait toujours créer mais ça ne coûte rien de vérifier. Évite un doublon inutile
            if not self.period_ids.filtered(lambda p: p.date_start == date_start and p.date_end == date_end_str):
                vals = {
                    'contract_id': self.id,
                    'number': i,
                    'date_start': fields.Date.to_string(ds),
                    'date_end': fields.Date.to_string(date_end)
                }
                period_obj.create(vals)
            ds = ds + relativedelta(months=self.period)
            if ds >= max_date:
                break

    @api.multi
    def action_view_intervention(self):
        action = self.env.ref('of_planning.of_sale_order_open_interventions').read()[0]
        interventions = self.line_ids.mapped('intervention_ids')
        action['domain'] = [('id', 'in', interventions._ids)]
        if len(self) == 1:
            action['context'] = {'default_contract_id': self.id}
        return action

    @api.multi
    def action_view_services(self):
        self.ensure_one()
        action = self.env.ref('of_service.action_of_service_prog_form_planning').read()[0]
        action['context'] = {
            'search_default_filter_ponc'  : 1,
            'search_default_contract_id'  : self.id,
            'default_recurrence'          : False,
        }
        return action

    @api.multi
    def faire_revision(self):
        """ Ouvre un wizard pour faire une révision à date """
        self.ensure_one()
        if not self.period_ids.filtered(lambda p: p.has_invoices):
            return self.env['of.popup.wizard'].popup_return(message=u"Aucune période ne pouvant être revue.")
        view_id = self.env.ref('of_contract_custom.of_contract_revision_view_form').id
        wizard = self.env['of.contract.revision.wizard'].create({
            'contract_id': self.id,
            'period_id': self.period_ids[0].id
        })
        return {
            'name'     : 'Avenant',
            'type'     : 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.contract.revision.wizard',
            'views'    : [(view_id, 'form')],
            'view_id'  : view_id,
            'target'   : 'new',
            'res_id'   : wizard.id,
            'context'  : self.env.context}

    @api.multi
    def avenant_de_masse(self):
        """ Ouvre un wizard pour faire une révision à date """
        self.ensure_one()
        view_id = self.env.ref('of_contract_custom.of_contract_mass_avenant_view_form').id
        lines = self.mapped('line_ids').filtered(lambda l: l.state == 'validated' and not l.line_avenant_id)
        wizard = self.env['of.contract.mass.avenant.wizard'].create({
            'date_start' : fields.Date.today(),
            'line_ids': [
                (0, 0, {'contract_line_id': line.id,}) for line in lines
                ]
        })
        return {
            'name'     : 'Avenant de masse',
            'type'     : 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.contract.mass.avenant.wizard',
            'views'    : [(view_id, 'form')],
            'view_id'  : view_id,
            'target'   : 'new',
            'res_id'   : wizard.id,
            'context'  : self.env.context}

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
            action = {'type': 'ir.actions.do_nothing'}
        return action

    @api.multi
    def valider_lignes_contrat(self):
        """ Valide toutes les lignes de contrat en brouillon """
        return self.line_ids.filtered(lambda s: s.state == 'draft').bouton_valider()

    @api.multi
    def _prepare_invoice(self, do_raise=True, intervention_id=False):
        """ Permet de récupérer un dictionnaire de valeur pour créer une facture """
        self.ensure_one()
        if not self.partner_id:
            if do_raise:
                raise ValidationError(
                    u"Vous devez d'abord sélectionner un client pour le contrat %s!" %
                    self.name)
            else:
                self.message_post(body=u"Création de la facture : "
                                       u"Vous devez d'abord sélectionner un client pour le contrat.")
                return False
        journal = self.journal_id or self.env['account.journal'].search(
            [('type', '=', 'sale'),
             ('company_id', '=', self.company_id.id)],
            limit=1)
        if not journal:
            if do_raise:
                raise ValidationError(
                    u"Veuillez définir un journal de vente pour votre société '%s'." %
                    (self.company_id.name or '',))
            else:
                self.message_post(body=u"Création de la facture : "
                                       u"Veuillez définir un journal de vente pour votre société.")
                return False
        currency = (
            self.pricelist_id.currency_id or
            self.partner_id.property_product_pricelist.currency_id or
            self.company_id.currency_id
        )
        # hasattr pour éviter une dépendance à of_tiers.
        # Permet de générer le compte comptable avant de le tenter dans _onchange_partner_id
        # Si la règle de génération est 'Sur toutes les sociétés comptables, dès qu'une société en a besoin'
        # le fait de générer un compte comptable sur une autre société vide le NewRecord
        if hasattr(self.partner_id, 'update_account'):
            self.partner_id.update_account()
        invoice = self.env['account.invoice'].new({
            'reference': self.name,
            'type': 'out_invoice',
            'partner_id': self.partner_id.address_get(
                ['invoice'])['invoice'],
            'currency_id': currency.id,
            'journal_id': journal.id,
            'date_invoice': self.recurring_next_date,
            'origin': 'Contrat %s' % self.name,
            'company_id': self.company_id.id,
            'of_contract_id': self.id,
            'user_id': self.partner_id.user_id.id,
            'fiscal_position_id': self.fiscal_position_id.id,
            'payment_term_id': self.payment_term_id.id,
            'of_intervention_id': intervention_id,
            'of_project_id': self.account_analytic_id and self.account_analytic_id.id,
        })
        # Get other invoice values from partner onchange
        invoice._onchange_partner_id()
        invoice.fiscal_position_id = self.fiscal_position_id.id
        invoice.payment_term_id = self.payment_term_id.id
        return invoice._convert_to_write(invoice._cache)

    @api.multi
    def _create_invoice(self, do_raise=True):
        """ Création des factures du contrats en fonction de si les lignes du contrat sont groupées ou non """
        self.ensure_one()
        lines = self.line_ids.filtered('is_invoiceable').filtered(
            lambda l: l.next_date == self.recurring_next_date)
        if not lines:
            if do_raise:
                raise UserError("Aucune ligne du contrat n'est facturable")
            else:
                self.message_post(body=u"Création de la facture : Aucune ligne du contrat n'est facturable.")
                return False
        lines_grouped = lines.filtered('grouped')
        single_lines = lines - lines_grouped
        invoices = self.env['account.invoice']
        if lines_grouped:
            invoice_vals = self._prepare_invoice(do_raise=do_raise)
            if not invoice_vals:
                return invoices
            lines = []
            for line in lines_grouped:
                lines += line._add_invoice_lines()
            if lines:
                addresses = lines_grouped.mapped('address_id')
                if len(addresses) == 1:
                    invoice_vals['partner_shipping_id'] = addresses.id
                invoice_vals['invoice_line_ids'] = lines
                invoice = self.env['account.invoice'].create(invoice_vals)
                invoice.compute_taxes()
                invoices |= invoice
        if single_lines:
            for line in single_lines:
                intervention_id = False
                if line.frequency_type == 'date':
                    last_invoicing = line.last_invoicing_date
                    if not last_invoicing:
                        date_start = fields.Date.from_string(line.date_contract_start)
                        last_invoicing = fields.Date.to_string(date_start - relativedelta(days=1))
                    interventions = line.intervention_ids.filtered(
                        lambda i: i.state == 'done' and i.date_date > last_invoicing)
                    if interventions:
                        interventions = interventions.sorted('date_date')
                        intervention_id = interventions[0].id
                invoice_vals = self._prepare_invoice(do_raise=do_raise, intervention_id=intervention_id)
                if not invoice_vals:
                    continue
                lines = line._add_invoice_lines()
                if not lines:
                    continue
                if line.address_id:
                    invoice_vals['partner_shipping_id'] = line.address_id.id
                invoice_vals['invoice_line_ids'] = lines
                invoice = self.env['account.invoice'].create(invoice_vals)
                invoice.compute_taxes()
                invoices |= invoice
        self.line_ids._auto_cancel()
        return invoices

    @api.multi
    def recurring_create_invoice(self, do_raise=True):
        """ Créer les factures pour une liste de contrats """
        invoices = self.env['account.invoice']
        for contract in self:
            if len(contract.line_ids) == 0 or not contract.line_ids.mapped('is_invoiceable'):
                if do_raise:
                    raise UserError(u"Impossible de créer une facture car le contrat n'a aucune ligne facturable "
                                    u"pour le contrat %s : %s." % (contract.name, contract.partner_id.name))
                else:
                    self.message_post(body=u"Création de la facture : "
                                           u"Impossible de créer une facture car "
                                           u"le contrat n'a aucune ligne facturable.")
            ref_date = contract.recurring_next_date
            if (contract.date_start > ref_date or
                    contract.date_end and contract.date_end < ref_date):
                if do_raise:
                    raise ValidationError(
                        u"Vous devez revoir les dates de début et de fin pour le contrat %s : %s." %
                        (contract.name, contract.partner_id.name)
                    )
                else:
                    self.message_post(body=u"Création de la facture : "
                                           u"Vous devez revoir les dates de début et de fin pour le contrat.")
            ctx = self.env.context.copy()
            ctx.update({
                # Force company for correct evaluation of domain access rules
                'force_company': contract.company_id.id,
            })
            # Re-read contract with correct company
            new_invoices = contract.with_context(ctx)._create_invoice(do_raise=do_raise)
            if new_invoices:
                invoices |= new_invoices
        return invoices

    @api.model
    def generate_invoices(self):
        """ Génére les facture pour les contrats à facturer aujourd'hui """
        today = fields.Date.today()
        contracts = self.search([('recurring_next_date', '<=', today)])
        contracts.recurring_create_invoice(do_raise=False)

    @api.multi
    def generate_revision_invoice(self, invoicing_date, do_raise=True):
        """ Génére la facture de révision sur une date donnée """
        self.ensure_one()
        invoice_obj = self.env['account.invoice']
        period = self.period_ids.filtered(lambda p: p.date_end == invoicing_date)
        if not period:
            return
        date_start = period.date_start
        lines = self.line_ids.filtered(lambda l: any([date_start <= i.date_invoice <= invoicing_date
                                                      for i in l.contract_product_ids.mapped('invoice_line_ids')
                                                     .mapped('invoice_id')]))
        if not lines:
            if do_raise:
                raise UserWarning("Aucune ligne du contrat n'est facturable")
            else:
                self.message_post(body=u"Création de la facture de révision : "
                                       u"Aucune ligne du contrat n'est facturable.")
                return False
        lines_grouped = lines.filtered('grouped')
        single_lines = lines - lines_grouped
        invoices = self.env['account.invoice']
        if lines_grouped:
            invoice_vals = self._prepare_invoice(do_raise=do_raise)
            if not invoice_vals:
                return invoices
            invoice_type, invoice_lines = lines_grouped.generate_revision_lines_grouped(invoicing_date)
            invoice_vals['type'] = invoice_type
            invoice_vals['invoice_line_ids'] = invoice_lines
            invoice_vals['date_invoice'] = invoicing_date
            invoice = invoice_obj.create(invoice_vals)
            invoice.compute_taxes()
            invoices |= invoice
        if single_lines:
            for line in single_lines:
                invoice_vals = self._prepare_invoice(do_raise=do_raise)
                if not invoice_vals:
                    continue
                total = 0
                invoice_lines = line.generate_revision_line(invoicing_date)
                if not invoice_lines:
                    continue
                for invoice_line in invoice_lines:
                    total += invoice_line['quantity'] * invoice_line['price_unit']
                if total < 0:
                    invoice_vals['type'] = 'out_refund'
                    for invoice_line in invoice_lines:
                        invoice_line['quantity'] = invoice_line['quantity'] * -1
                invoice_vals['invoice_line_ids'] = [(0, 0, invoice_line) for invoice_line in invoice_lines]
                invoice_vals['date_invoice'] = invoicing_date
                invoice = invoice_obj.create(invoice_vals)
                invoice.compute_taxes()
                invoices |= invoice
        return invoices

    @api.multi
    def button_renew(self):
        self = self.with_context(button_renew=True)
        automatic_renewal = self.env['of.contract']
        for contract in self:
            if contract.renewal:
                automatic_renewal |= contract
                continue
            current_end = fields.Date.from_string(contract.date_end)
            new_end = current_end + relativedelta(years=1)
            contract.date_end = fields.Date.to_string(new_end)
        ids_list = safe_eval(self.env['ir.config_parameter'].get_param('contracts_to_do', '[]'))
        ids_list += [contract_id for contract_id in self._ids if contract_id not in ids_list]
        self.env['ir.config_parameter'].set_param('contracts_to_do', '%s' % ids_list)
        if automatic_renewal:
            message = u"Les contrats suivants sont en renouvellement automatique, " + \
                      u"et n'ont donc pas été renouvelés :\n%s" % '\n'.join(c.name for c in automatic_renewal)
            return self.env['of.popup.wizard'].popup_return(message=message)
        return {'type': 'ir.actions.do_nothing'}

    @api.multi
    def of_get_report_name(self, docs):
        return "Contrat"

    @api.multi
    def of_get_report_number(self, docs):
        return self.reference

    @api.multi
    def of_get_report_date(self, docs):
        return fields.Date.today()

    @api.model
    def cron_generate_contract_di(self):
        ids_list = safe_eval(self.env['ir.config_parameter'].get_param('contracts_to_do', '[]'))
        contracts = self.search([('id', 'in', ids_list)])
        for contract in contracts:
            contract.line_ids._generate_services()
        self.env['ir.config_parameter'].set_param('contracts_to_do', '[]')


class OfContractLine(models.Model):
    _name = 'of.contract.line'
    _inherit = ["of.form.readonly", "of.planning.plannification"]
    _order = 'line_avenant_id ASC, code_de_ligne DESC'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        cr.execute(
            "SELECT * FROM information_schema.columns "
            "WHERE table_name = '%s' AND column_name = 'interv_frequency_nbr'" % (self._table,))
        exist1 = bool(cr.fetchall())
        cr.execute(
            "SELECT * FROM information_schema.columns "
            "WHERE table_name = '%s' AND column_name = 'nbr_interv'" % (self._table,))
        exist2 = bool(cr.fetchall())
        change_planif = False
        if exist2 and not exist1:
            cr.execute(
                "SELECT ocl.id, ocl.nbr_interv, sub.nbr_month "
                "FROM of_contract_line AS ocl "
                "JOIN (SELECT rel.of_contract_line_id AS line_id, count(rel.of_mois_id) AS nbr_month "
                "FROM of_contract_line_of_mois_rel AS rel "
                "GROUP BY rel.of_contract_line_id) AS sub ON sub.line_id=ocl.id")
            change_planif = cr.fetchall()
        res = super(OfContractLine, self)._auto_init()
        if change_planif:
            for line_id, nbr_interv, nbr_month in change_planif:
                if (float(nbr_interv)/float(nbr_month)).is_integer():
                    ratio = nbr_interv/nbr_month
                    values = ('month', ratio, line_id)
                else:
                    values = ('year', nbr_interv, line_id)
                cr.execute("UPDATE of_contract_line "
                           "SET interv_frequency = %s, interv_frequency_nbr = %s WHERE id = %s", values)
        return res

    name = fields.Char(string="Nom", compute="_compute_name", store=True)
    partner_id = fields.Many2one('res.partner', related="contract_id.partner_id", string="Client payeur", readonly=True)
    department_id = fields.Many2one(
        'res.country.department', related='partner_id.department_id', string=u"Département", readonly=True, store=True)
    address_id = fields.Many2one('res.partner', string="Adresse d'intervention", required=True)
    partner_code_magasin = fields.Char(string="Code magasin", related="address_id.of_code_magasin", readonly=True)
    address_street = fields.Char(string="Rue", related="address_id.street", readonly=True)
    address_street2 = fields.Char(string="Rue", related="address_id.street2", readonly=True)
    address_zip = fields.Char(string="Zip", related="address_id.zip", readonly=True)
    address_city = fields.Char(string="Ville", related="address_id.city", readonly=True)
    contract_id = fields.Many2one('of.contract', string=u"Contrat", required=True)
    company_id = fields.Many2one('res.company', related="contract_id.company_id", string='Société')
    supplier_id = fields.Many2one('res.partner', string="Prestataire", domain="[('supplier','=',True)]")
    supplier_tag_ids = fields.Many2many("res.partner.category", related="supplier_id.category_id",
                                        string=u"Étiquettes prestataire")
    type = fields.Selection([
        ('initial', 'Initiale'),
        ('avenant', 'Avenant')
        ], string="Type", readonly=True, default='initial', required=True)
    frequency_type = fields.Selection([
        ('date', u'À la prestation'),
        ('month', 'Mensuelle'),
        ('trimester', u'Trimestrielle'),  # Tout les 3 mois
        ('semester', u'Semestrielle'),  # 2 fois par ans
        ('year', u'Annuelle'),
        ], default='month', string=u"Fréquence de facturation", required=True)
    recurring_invoicing_payment_id = fields.Many2one(
        'of.contract.recurring.invoicing.payment', string="Type de facturation", required=True,
        default=lambda s: s.env.ref(
            'of_contract_custom.of_contract_recurring_invoicing_payment_pre-paid', raise_if_not_found=False))

    next_date = fields.Date(string="Prochaine facturation", compute="_compute_dates", store=True, copy=False)
    is_invoiceable = fields.Boolean(compute="_compute_is_invoiceable", store=True, copy=False)
    date_avenant = fields.Date(u'Date de début (avenant)', copy=False)
    date_start = fields.Date(
        u'Date de début', copy=False,
        help=u"N'est renseigné que si la ligne a été créée après la première facturation et n'est pas un avenant.")
    date_contract_start = fields.Date(u'Date de début', compute="_compute_dates")
    date_end = fields.Date(string="Date de fin de facturation", copy=False)
    date_contract_end = fields.Date(u'Date de fin', compute="_compute_dates", store=True)
    current_period_id = fields.Many2one(
        comodel_name='of.contract.period', string=u"Période du contrat",
        compute="_compute_current_period_id", store=True, copy=False)
    code_de_ligne = fields.Char(string="Code de ligne", copy=False)
    grouped = fields.Boolean(string="Regrouper la facturation")
    line_avenant_id = fields.Many2one(comodel_name='of.contract.line', string='Avenant', copy=False)
    line_origine_id = fields.Many2one(comodel_name='of.contract.line', string=u'Ligne liée', compute='_compute_origine')

    note = fields.Text(string="Description")
    parc_installe_id = fields.Many2one('of.parc.installe', string=u"No de série",
        domain="partner_id and [('client_id', '=', partner_id), '|', ('site_adresse_id', '=', False), ('site_adresse_id', '=', address_id)] or "
               "address_id and [('client_id', 'parent_of', address_id), '|', ('site_adresse_id', '=', False), ('site_adresse_id', '=', address_id)] or []")

    parc_installe_product_id = fields.Many2one(
        'product.product', string=u"Désignation", related="parc_installe_id.product_id", readonly=True)
    parc_installe_site_adresse_id = fields.Many2one(
        'res.partner', string=u"Adresse de pose", related="parc_installe_id.site_adresse_id", readonly=True)
    parc_installe_note = fields.Text(string=u"Note", related="parc_installe_id.note", readonly=True)
    recurring_interval = fields.Integer(string=u'Répéter chaque', default=1)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', u'Validée'),
        ('cancel', u'Annulée'),
    ], string=u"État", copy=False, required=True, default='draft')

    company_currency_id = fields.Many2one(
        'res.currency', related='contract_id.company_id.currency_id', string="Company Currency", readonly=True)
    invoice_line_ids = fields.One2many(
        'account.invoice.line', 'of_contract_line_id', string="Lignes de factures", readonly=True)
    invoice_count = fields.Integer(string="Nombre de factures", compute='_compute_invoice_count')
    contract_product_ids = fields.One2many(
        comodel_name="of.contract.product", inverse_name='line_id', string="Articles", copy=False)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale")
    next_purchase_price = fields.Float(string=u"Prochain coût", compute='_compute_prices')
    year_purchase_price = fields.Float(string=u"Coût annuel", compute='_compute_prices')
    amount_subtotal = fields.Monetary(
        string="Prochain Total HT", compute='_compute_prices', currency_field='company_currency_id',
        digits=dp.get_precision('Account'), store=True, copy=False)
    amount_taxes = fields.Monetary(
        string="Taxes ", compute='_compute_prices', currency_field='company_currency_id', store=True, copy=False)
    amount_total = fields.Monetary(
        string="Prochain Total", compute='_compute_prices', currency_field='company_currency_id', store=True,
        copy=False)
    year_subtotal = fields.Float(
        string="Total HT annuel", compute='_compute_prices', digits=dp.get_precision('Account'), store=True)
    year_taxes = fields.Monetary(
        string="Taxes annuelles", compute='_compute_prices', currency_field='company_currency_id', store=True)
    year_total = fields.Monetary(
        string="Total annuel", compute='_compute_prices', currency_field='company_currency_id', store=True)

    service_ids = fields.One2many(
            comodel_name='of.service', inverse_name='contract_line_id', string=u"Demandes d'intervention")
    service_count = fields.Integer(string="Nb demandes", compute="_compute_service_count")
    intervention_ids = fields.One2many(
            comodel_name='of.planning.intervention', inverse_name='contract_line_id', string="RDVs d'interventions")
    intervention_count = fields.Integer(string="Nbr RDVs", compute="_compute_intervention_count")

    revision = fields.Selection([
        ('none', 'Aucune'),
        ('last_day', 'Dernier jour du contrat'),
        ], string=u"Période de révision", default='last_day')

    contract_current_period_id = fields.Many2one(
        comodel_name='of.contract.period', string=u"Période du contrat", related="contract_id.current_period_id",
        readonly=True)
    contract_date_start = fields.Date(string=u'Date de souscription', related="contract_id.date_start", readonly=True)
    contract_date_end = fields.Date(string='Date de fin', related="contract_id.date_end", readonly=True)
    contract_type = fields.Selection([
        ('simple', u'Simplifié'),
        ('advanced', u'Avancé'),
        ], string="Type de contrat", related="contract_id.contract_type", readonly=True, default='simple')
    contract_renewal = fields.Boolean(string="Renouvellement automatique", related="contract_id.renewal", readonly=True)
    use_index = fields.Boolean(string="Indexer", default=True)
    date_indexed = fields.Date(string=u"Dernière indexation", compute="_compute_date_indexed", store=True)
    last_invoicing_date = fields.Date(
            string=u"Dernière facturation", copy=False, compute="_compute_dates", store=True)
    afficher_facturation = fields.Boolean(string=u"Détails facturation")
    revision_avenant = fields.Boolean(string=u"")
    warning_planif = fields.Boolean(string="Warning planification", compute="_compute_warning_planif")

    use_sav = fields.Boolean(string="Utilise les SAV")
    sav_count = fields.Integer(string="Nombre de visites SAV")
    remaining_sav = fields.Integer(string="Nbr. visites SAV restantes", compute="_compute_remaining_sav")
    notes = fields.Text(string="Notes")

    @api.depends('code_de_ligne',
                 'line_avenant_id', 'line_avenant_id.code_de_ligne',
                 'state',
                 'is_invoiceable')
    def _compute_name(self):
        """ Calcul du nom de la ligne en fonction de l'état et du code de ligne """
        for line in self:
            if line.state == 'draft':
                line.name = u'Ligne brouillon'
            elif line.line_avenant_id and line.state == 'cancel':
                line.name = u'Ligne %s annulée par avenant %s' % (line.code_de_ligne,
                                                                  line.line_avenant_id.code_de_ligne or u'brouillon')
            else:
                line.name = u'Ligne %s' % line.code_de_ligne

    @api.depends('next_date', 'date_contract_end', 'contract_id', 'contract_id.period_ids')
    def _compute_current_period_id(self):
        """ Calcule la période courante """
        for line in self:
            if not line.contract_id.period_ids:
                continue
            if line.date_end:
                ref_date = line.date_end
            else:
                ref_date = line.next_date or line.date_contract_end
            if not ref_date:
                continue
            line.current_period_id = line.contract_id.period_ids\
                                                     .filtered(lambda p: p.date_start <= ref_date <= p.date_end)

    @api.depends('intervention_ids',
                 'intervention_ids.state',
                 'contract_product_ids',
                 'next_date', 'frequency_type',
                 'contract_id',
                 'contract_id.recurring_next_date',
                 'state')
    def _compute_is_invoiceable(self):
        """ Calcule si la ligne de contrat peut être facturée """
        for service in self:
            if service.state == 'validated':
                if service.contract_product_ids and service.next_date \
                   and service.next_date == service.contract_id.recurring_next_date:
                    service.is_invoiceable = True
                else:
                    service.is_invoiceable = False
            else:
                service.is_invoiceable = False

    @api.depends('frequency_type', 'invoice_line_ids',
                 'invoice_line_ids.date_invoice',
                 'invoice_line_ids.of_contract_supposed_date',
                 'invoice_line_ids.invoice_id',
                 'invoice_line_ids.invoice_id.state',
                 'date_avenant',
                 'last_invoicing_date',
                 'date_end',
                 'contract_id.date_start',
                 'contract_id.date_end',
                 'contract_id.last_invoicing_date',
                 'state',
                 'intervention_ids',
                 'intervention_ids.state')
    def _compute_dates(self):
        """ Calcul des différentes dates utilisées pour la facturation """
        for line in self:
            if not line.contract_id:
                continue
            # date start
            frequency_type = line.frequency_type
            if line.date_avenant:
                line.date_contract_start = line.date_avenant
            elif line.date_start:
                line.date_contract_start = line.date_start
            elif line.contract_id.last_invoicing_date:
                line.date_contract_start = line.contract_id.last_invoicing_date
            elif line.contract_id.date_start:
                line.date_contract_start = line.contract_id.date_start
            # date_end
            if line.date_end:
                line.date_contract_end = line.date_end
            elif line.contract_id.date_end:
                line.date_contract_end = line.contract_id.date_end
            last_invoice_date = False
            if line.invoice_line_ids.filtered(lambda il: il.invoice_id.state != 'cancel'):
                invoice_lines = line.invoice_line_ids.filtered(lambda i: i.invoice_id.state != 'cancel')\
                                                .sorted('of_contract_supposed_date')
                last_invoice_date = invoice_lines[-1].of_contract_supposed_date
                line.last_invoicing_date = invoice_lines[-1].invoice_id.date_invoice
            # On entre dans ce cas quand la ligne est un avenant et n'a pas encore été facturée donc on vérifie
            # la ligne qui a généré cet avenant
            elif line.line_origine_id.invoice_line_ids:
                last_invoice_date = line.line_origine_id\
                                        .invoice_line_ids.filtered(lambda il: il.invoice_id.state != 'cancel')\
                                        .sorted('date_invoice')[-1].of_contract_supposed_date
            if line.state != 'validated':
                continue
            if line.frequency_type == 'date':
                # line.recurring_invoicing_payment_id.code est 'date' ou 'post-paid'
                invoice_lines = line.invoice_line_ids.filtered(lambda i: i.invoice_id.state != 'cancel') \
                                                     .sorted('of_contract_supposed_date')
                if invoice_lines:
                    last_invoicing = invoice_lines[-1].of_contract_supposed_date
                else:
                    date_start = fields.Date.from_string(line.date_contract_start)
                    last_invoicing = fields.Date.to_string(date_start - relativedelta(days=1))
                interventions = line.intervention_ids\
                                    .filtered(lambda i: i.state == 'done' and i.date_date > last_invoicing)
                if interventions:
                    next_date = interventions.sorted('date_date')[0].date_date
                    if line.recurring_invoicing_payment_id.code == 'post-paid':
                        # On se place au dernier jour du mois
                        base_date = fields.Date.from_string(next_date)
                        next_date = base_date + relativedelta(months=1, day=1, days=-1)
                    line.next_date = next_date
            else:
                invoice_lines = line.invoice_line_ids.filtered(lambda l: l.invoice_id.state != 'cancel')
                if not invoice_lines:
                    base_date = fields.Date.from_string(last_invoice_date or line.date_contract_start)
                    end = fields.Date.from_string(line.date_contract_end)
                    next_date = False
                    if line.recurring_invoicing_payment_id.code == 'pre-paid':
                        if last_invoice_date:
                            if frequency_type == 'month':
                                next_date = base_date + relativedelta(months=1, day=1)
                            if frequency_type == 'trimester':
                                next_date = base_date + relativedelta(months=3, day=1)
                            if frequency_type == 'semester':
                                next_date = base_date + relativedelta(months=6, day=1)
                            if frequency_type == 'year':
                                next_date = base_date + relativedelta(years=1, month=1, day=1)
                        else:
                            if base_date.day != 1:
                                base_date = base_date + relativedelta(months=1)
                            next_date = base_date + relativedelta(day=1)
                    else:
                        if frequency_type == 'month':
                            next_date = base_date + relativedelta(months=1, day=1, days=-1)
                        if frequency_type == 'trimester':
                            next_date = base_date + relativedelta(months=3, day=1, days=-1)
                        if frequency_type == 'semester':
                            next_date = base_date + relativedelta(months=6, day=1, days=-1)
                        if frequency_type == 'year':
                            next_date = base_date + relativedelta(years=1, month=1, day=1, days=-1)
                    if next_date and (not end or end > next_date):
                        line.next_date = next_date
                    continue
                elif last_invoice_date:
                    end = line.date_contract_end
                    if line.frequency_type == 'month':
                        next = fields.Date.from_string(last_invoice_date) + relativedelta(months=1)
                        if line.recurring_invoicing_payment_id.code == 'pre-paid':
                            next = next + relativedelta(day=1)
                        else:
                            next = next + relativedelta(months=1, day=1, days=-1)
                        next = fields.Date.to_string(next)
                        if not end or end > next:
                            line.next_date = next
                    elif line.frequency_type == 'trimester':
                        next = fields.Date.from_string(last_invoice_date) + relativedelta(months=3)
                        if line.recurring_invoicing_payment_id.code == 'pre-paid':
                            next = next + relativedelta(day=1)
                        else:
                            next = next + relativedelta(months=1, day=1, days=-1)
                        next = fields.Date.to_string(next)
                        if not end or end > next:
                            line.next_date = next
                    elif line.frequency_type == 'semester':
                        next = fields.Date.from_string(last_invoice_date) + relativedelta(months=6)
                        if line.recurring_invoicing_payment_id.code == 'pre-paid':
                            next = next + relativedelta(day=1)
                        else:
                            next = next + relativedelta(months=1, day=1, days=-1)
                        next = fields.Date.to_string(next)
                        if not end or end > next:
                            line.next_date = next
                    elif line.frequency_type == 'year':
                        next = fields.Date.from_string(last_invoice_date) + relativedelta(years=1)
                        if line.recurring_invoicing_payment_id.code == 'pre-paid':
                            next = next + relativedelta(day=1)
                        else:
                            next = next + relativedelta(months=1, day=1, days=-1)
                        next = fields.Date.to_string(next)
                        if not end or end > next:
                            line.next_date = next

    @api.depends('contract_product_ids',
                 'contract_product_ids.product_id',
                 'contract_product_ids.price_unit',
                 'contract_product_ids.amount_subtotal',
                 'contract_product_ids.year_subtotal',
                 'contract_product_ids.amount_taxes',
                 'contract_product_ids.year_taxes',
                 'contract_product_ids.next_purchase_price',
                 'contract_product_ids.year_purchase_price',
                 'frequency_type',
                 'fiscal_position_id')
    def _compute_prices(self):
        """ Calcule les différents montants facturés générés par la ligne de contrat """
        for contract_line in self:
            # For a single month
            product_lines = contract_line.contract_product_ids
            c_subtotal = round(sum(product_lines.mapped('amount_subtotal')), 2)
            c_total_tax = round(sum(product_lines.mapped('amount_taxes')), 2)
            contract_line.amount_taxes = c_total_tax
            contract_line.amount_subtotal = c_subtotal
            contract_line.amount_total = c_total_tax + c_subtotal
            contract_line.next_purchase_price = round(sum(product_lines.mapped('next_purchase_price')), 2)
            # For a year
            product_lines = contract_line.contract_product_ids
            c_subtotal = round(sum(product_lines.mapped('year_subtotal')), 2)
            c_total_tax = round(sum(product_lines.mapped('year_taxes')), 2)
            contract_line.year_taxes = c_total_tax
            contract_line.year_subtotal = c_subtotal
            contract_line.year_total = c_total_tax + c_subtotal
            contract_line.year_purchase_price = round(sum(product_lines.mapped('year_purchase_price')), 2)

    @api.depends('service_ids')
    def _compute_service_count(self):
        """ Calcul du nombre de demandes d'intervention """
        for line in self:
            line.service_count = len(line.service_ids)

    @api.depends('intervention_ids')
    def _compute_intervention_count(self):
        """ Calcul du nombre de RDVs d'interventions """
        for line in self:
            line.intervention_count = len(line.intervention_ids)

    @api.depends('invoice_line_ids')
    def _compute_invoice_count(self):
        """ Calcul du nombre de factures """
        for line in self:
            line.invoice_count = len(line.invoice_line_ids.mapped('invoice_id'))

    @api.multi
    def _compute_origine(self):
        """ Calcul de la ligne de contrat d'origine (n'est rempli que si la ligne est un avenant) """
        contract_line_obj = self.env['of.contract.line']
        for line in self:
            line.line_origine_id = contract_line_obj.search([('line_avenant_id', '=', line.id)], limit=1)

    @api.depends('contract_product_ids', 'contract_product_ids.date_indexed')
    def _compute_date_indexed(self):
        for line in self:
            products = line.contract_product_ids.filtered('date_indexed').sorted('date_indexed')
            if products:
                line.date_indexed = products[-1].date_indexed

    @api.depends()
    def _compute_warning_planif(self):
        today = fields.Date.today()
        today_dt = fields.Date.from_string(today)
        for line in self:
            if line.date_contract_end and today > line.date_contract_end:
                continue
            in_30_days = today_dt + relativedelta(days=30)
            if fields.Date.to_string(in_30_days) >= line.current_period_id.date_end:
                period = line.current_period_id
                rdvs = line.intervention_ids.filtered(lambda i: i.state in ('draft', 'confirmed', 'done') and
                                                                period.date_start <= i.date_date <= period.date_end)
                if len(rdvs) < line.nbr_interv:
                    line.warning_planif = True

    @api.depends('sav_count', 'service_ids')
    def _compute_remaining_sav(self):
        sav_type = self.env.ref('of_service_parc_installe.of_service_type_sav', raise_if_not_found=False)
        if sav_type:
            for line in self:
                period = line.current_period_id
                period_start = period.date_start
                period_end = period.date_end
                sav = line.service_ids.filtered(lambda s: s.type_id.id == sav_type.id and
                                                se_chevauchent(s.date_next, s.date_fin, period_start, period_end))
                remaining_sav = line.sav_count - len(sav)
                line.remaining_sav = remaining_sav if remaining_sav > 0 else 0

    @api.onchange('address_id')
    def _onchange_address_id(self):
        """ Récupération du parc installé si l'utilisateur à les droits """
        self.ensure_one()
        if self.address_id:
            if self.address_id.of_prestataire_id:
                self.supplier_id = self.address_id.of_prestataire_id
            parc_obj = self.env['of.parc.installe']
            # ne pas tenter le onchange si l'utilisateur n'a pas les droits
            if not parc_obj.check_access_rights('read', raise_exception=False):
                return
            partner = self.partner_id
            address = self.address_id
            if partner:
                parc_installe = parc_obj.search([('client_id', '=', partner.id),
                                                 '|', ('site_adresse_id', '=', False),
                                                      ('site_adresse_id', '=', address.id)],
                                                limit=1)
            else:
                parc_installe = parc_obj.search([('client_id', '=', self.address_id.id),
                                                 '|', ('site_adresse_id', '=', False),
                                                      ('site_adresse_id', '=', address.id)],
                                                limit=1)
            if parc_installe:
                self.parc_installe_id = parc_installe

    @api.onchange('frequency_type')
    def _onchange_frequency_type(self):
        self.ensure_one()
        if self.frequency_type == 'date':
            if self.recurring_invoicing_payment_id.code not in ('date', 'post-paid'):
                self.recurring_invoicing_payment_id = False
        elif self.frequency_type:
            if self.recurring_invoicing_payment_id.code not in ('pre-paid', 'post-paid'):
                self.recurring_invoicing_payment_id = False

    @api.model
    def cancel_contract_lines(self):
        today = fields.Date.today()
        lines_to_cancel = self.search([('date_contract_end', '<=', today), ('state', '=', 'validated')])
        lines_to_cancel.write({'state': 'cancel'})

    @api.multi
    def name_get(self):
        if self._context.get('display_address', False):
            result = []
            for record in self:
                result.append((
                    record.id, record.name + " - %s" % record.address_id.name))
            return result
        else:
            return super(OfContractLine, self).name_get()

    @api.model
    def create(self, vals):
        """ Affectation du numéro si création à l'état 'validated' """
        res = super(OfContractLine, self).create(vals)
        res._affect_number()
        return res

    @api.multi
    def write(self, vals):
        """ Affectation du numéro si passage à l'état 'validated' """
        fields_allowed = self.get_write_allowed_fields()
        if 'contract_id' in vals:  # On ne doit pas changer de contrat après la création
            del vals['contract_id']
        if len(self) == 1:
            # Dans certains cas, la modification de la date de fin du contrat peut faire en sorte de renvoyer tous
            # les champs des lignes de contrats même si ils n'ont pas été modifiés.
            # vals contient la liste des champs de la vue tree.
            # Ce bout de code a pour but de retirer les valeurs non modifiées pour éviter un blocage du write dû à
            # la modification de champ non autorisés après la validation d'une ligne.
            keys_to_delete = []
            fields_list = self._fields
            fields_to_check = []
            for key, val in vals.iteritems():
                if not fields_list[key].store and not fields_list[key].type.endswith('2many'):
                    keys_to_delete.append(key)
                elif fields_list[key].type.endswith('2many'):
                    continue  # la vérification des x2many ne devrait pas être faite ici, il faut ignorer ces champs
                else:
                    fields_to_check.append(key)
            for key in keys_to_delete:
                del vals[key]
            for field_name in fields_to_check:
                val = vals[field_name]  # nouvelle valeur
                self_val = self[field_name]  # valeur actuelle
                if val == self_val or (isinstance(self_val, models.Model) and self_val.id == val):
                    del vals[field_name]

        if not self._context.get('no_verification'):
            for line in self:
                if line.state == 'validated' and any([key not in fields_allowed for key in vals.keys()]):
                    fields_string = '\n'.join([self._fields[field].string for field in fields_allowed])
                    raise UserError(u'Pour les lignes de contrats validées, '
                                    u'vous ne pouvez modifier que les champs suivants :\n%s' % fields_string)
        res = super(OfContractLine, self).write(vals)
        self._affect_number()
        for line in self:
            if ('supplier_id' in vals and line.state == 'validated') or vals.get('state', '') == 'validated':
                supplier_id = vals.get('supplier_id', line.supplier_id.id)
                if line.address_id.of_prestataire_id and line.address_id.of_prestataire_id.id != supplier_id \
                   or not line.address_id.of_prestataire_id:
                    line.address_id.write({'of_prestataire_id': supplier_id})
        return res

    @api.multi
    def _write(self, vals):
        """ Génération d'une facture de revision pour l'avenant """
        for contract_line in self:
            if 'next_date' in vals and contract_line.revision_avenant and contract_line.state == 'validated':
                contract_line._revision_avenant()
                vals['revision_avenant'] = False
        res = super(OfContractLine, self)._write(vals)
        if not self.env.context.get('button_renew', False):
            self._generate_services()
        return res

    @api.multi
    def unlink(self):
        if any([state != 'draft' for state in self.mapped('state')]):
            raise UserError("Vous ne pouvez supprimer que des lignes en brouillon.")
        for line in self:
            if line.line_origine_id:
                line.line_origine_id.with_context(no_verification=True).write({
                    'line_avenant_id': False,
                    'date_end'       : False,
                })
        return super(OfContractLine, self).unlink()

    @api.model
    def get_write_allowed_fields(self):
        return ['state', 'supplier_id', 'afficher_facturation', 'grouped', 'mois_reference_ids', 'notes',
                'date_contract_end', 'fiscal_position_id', 'use_index', 'revision']

    @api.multi
    def _affect_number(self):
        """ Affectation du code de ligne """
        sequence = self.env.ref('of_contract_custom.of_contract_custom_sequence')
        for contract_line in self:
            if contract_line.state == 'validated' and not contract_line.code_de_ligne:
                contract_line.with_context(no_verification=True).write({'code_de_ligne': sequence.next_by_id()})

    @api.multi
    def bouton_valider(self):
        """ Valide la ligne de contrat """
        no_product = False
        for line in self:
            if line.contract_type == 'advanced' and not line.contract_product_ids:
                no_product = line
                continue
            line.write({'state': 'validated'})
        if no_product:
            return self.env['of.popup.wizard'].popup_return(
                    message=u"La ligne %s ne peut pas être validée car elle n'a pas d'article" % no_product.name)

    @api.multi
    def bouton_brouillon(self):
        """ Remettre la ligne de contrat en brouillon """
        if self.state == 'validated':
            self.write({'state': 'draft'})
            self.remove_services()
        else:
            return self.env['of.popup.wizard'].popup_return(
                message=u"Vous ne pouvez pas remettre en brouillon une ligne annulée.")


    @api.multi
    def faire_avenant(self):
        """ Renvoi un wizard pour créer un avenant sur la ligne de contrat sélectionnée """
        self.ensure_one()
        view_id = self.env.ref('of_contract_custom.of_contract_avenant_view_form').id
        wizard = self.env['of.contract.avenant.wizard'].create({'contract_line_id': self.id})
        return {
            'name'     : 'Avenant',
            'type'     : 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.contract.avenant.wizard',
            'views'    : [(view_id, 'form')],
            'view_id'  : view_id,
            'target'   : 'new',
            'res_id'   : wizard.id,
            'context'  : self.env.context}

    @api.multi
    def annuler_la_ligne(self):
        """ Renvoi un wizard permettant de donner une date de fin à la ligne de contrat"""
        self.ensure_one()
        view_id = self.env.ref('of_contract_custom.of_contract_line_cancel_view_form').id
        ref_date = fields.Date.today()
        if self.last_invoicing_date and self.last_invoicing_date > ref_date:
            ref_date = self.last_invoicing_date
        wizard = self.env['of.contract.line.cancel.wizard'].create({'contract_line_id': self.id, 'date_end': ref_date})
        return {
            'name'     : 'Avenant',
            'type'     : 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'of.contract.line.cancel.wizard',
            'views'    : [(view_id, 'form')],
            'view_id'  : view_id,
            'target'   : 'new',
            'res_id'   : wizard.id,
            'context'  : self.env.context}

    @api.multi
    def supprimer_la_ligne(self):
        """ Supprime une ligne de contrat uniquement si à l'état brouillon"""
        self.ensure_one()
        if self.state == 'draft':
            self.unlink()

    @api.multi
    def action_view_services(self):
        self.ensure_one()
        action = self.env.ref('of_service.action_of_service_prog_form_planning').read()[0]
        action['context'] = {
            'search_default_filter_ponc': 1,
            'search_default_contract_line_id': self.id,
            # 'search_default_date_range_id': self.date_range_id.id,
            'default_recurrence': False,
        }
        return action

    @api.multi
    def action_view_invoices(self):
        invoices = self.invoice_line_ids.mapped('invoice_id')
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.multi
    def action_view_intervention(self):
        action = self.env.ref('of_planning.action_of_planning_intervention_calendar').read()[0]
        action['context'] = {'search_default_contract_line_id': self.id}
        return action

    @api.multi
    def _add_invoice_lines(self):
        """
        Récupère un dictionnaire de valeurs pour chaque ligne de produit et créer une ligne de facture par article
        """
        self.ensure_one()
        lines = []
        for product_line in self.contract_product_ids:
            invoice_line_vals = product_line._prepare_invoice_line()
            invoice_line_vals.update({
                'of_contract_line_id': self.id,
                })
            lines.append((0, 0, invoice_line_vals))
        return lines

    @api.multi
    def _prepare_service_values(self):
        self.ensure_one()
        ttype = self.env.ref('of_service.of_service_type_maintenance')
        return {
            'type_id': ttype.id,
            'partner_id': self.partner_id.id,
            'address_id': self.address_id.id,
            'tache_id': self.tache_id.id,
            'recurrence': False,
            'contract_id': self.contract_id.id,
            'contract_line_id': self.id,
            'note': self.notes,
            'supplier_id': self.supplier_id.id or False,
            'company_id': self.company_id.id,
        }

    @api.multi
    def _auto_cancel(self):
        """Passe l'état de la ligne à "Annulée" si elle n'a pas de date de prochaine facturation et a un avenant"""
        for line in self:
            if line.state == 'validated' and not line.next_date and line.line_avenant_id:
                line.state = 'cancel'

    @api.multi
    def _generate_services(self):
        """ Génération des demandes d'interventions """
        Service = self.with_context(bloquer_recurrence=True).env['of.service']
        li = [(line, line.current_period_id) for line in self]
        for line, period in li:
            if not period or line.state != 'validated':
                continue
            services = self.env['of.service']
            months = line.mois_reference_ids
            nbr_intervs = line.nbr_interv
            nbr_months = len(months)
            ratio = float(nbr_intervs) / float(nbr_months)
            if not nbr_intervs or not nbr_months:
                continue
            date_start_da = fields.Date.from_string(period.date_start)
            for i in xrange(0, nbr_intervs):
                if len(line.service_ids.filtered(
                        lambda s: period.date_start <= s.date_next < period.date_end)) >= nbr_intervs:
                    break
                month = months[int(i/ratio)]
                num_mois = month.numero
                service_da = date_start_da + relativedelta(
                    years=int(date_start_da.month > num_mois), month=num_mois, day=1)
                date_service = fields.Date.to_string(service_da)
                month_service_end = fields.Date.to_string(service_da + relativedelta(months=1))
                if line.date_end and date_service > line.date_end:
                    break
                if len(line.service_ids.filtered(
                        lambda s: date_service <= s.date_next < month_service_end)) >= round(ratio):
                    continue

                new_service = Service.new(line._prepare_service_values())
                new_service._onchange_tache_id()
                new_service.update({'date_next': date_service})
                new_service._onchange_date_next()
                if line.parc_installe_id:
                    new_service.update({'parc_installe_id': line.parc_installe_id.id})
                new_service_vals = new_service._convert_to_write(new_service._cache)
                lines = []
                for product_line in line.contract_product_ids:
                    qty = product_line.qty_per_period / nbr_intervs
                    lines.append((0, 0, {
                        'qty': qty,
                        'product_id': product_line.product_id.id,
                        'name': product_line.name,
                        'price_unit': product_line.price_unit,
                        'discount': product_line.discount,
                        'taxe_ids': [(4, tax.id) for tax in product_line.tax_ids],
                        'of_contract_line_id': line.id,
                        'of_contract_product_id': product_line.id,
                    }))
                new_service_vals['line_ids'] = lines
                if line.fiscal_position_id:
                    new_service_vals['fiscal_position_id'] = line.fiscal_position_id.id
                new_service = Service.create(new_service_vals)
                services |= new_service
            if services:
                services.button_valider()

    @api.multi
    def generate_revision_line(self, invoicing_date):
        """ Récupération des valeurs pour les lignes de facture de révision de la ligne de contrat """
        self.ensure_one()
        lines = []
        for product_line in self.contract_product_ids:
            period = product_line.line_id.contract_id.period_ids.filtered(lambda p: p.date_end == invoicing_date)
            if not period:
                return
            date_start = period.date_start
            next_product = product_line.next_product_id
            if next_product.invoice_line_ids\
                           .filtered(lambda l: l.invoice_id.state != 'cancel'
                                               and date_start <= l.invoice_id.date_invoice <= invoicing_date):
                continue

            if next_product.line_id.intervention_ids.filtered(lambda i: date_start <= i.date_date <= invoicing_date
                                                                        and i.state == 'done'):
                continue

            qty_invoiced = product_line._get_quantity_invoiced_on_period(period)
            qty_done = product_line._get_quantity_done_on_period(period)
            qty_to_invoice = qty_done - qty_invoiced
            if not qty_to_invoice:
                continue
            vals = product_line._prepare_invoice_line()
            vals['quantity'] = qty_to_invoice
            lines.append(vals)
        return lines

    @api.multi
    def generate_revision_lines_grouped(self, invoicing_date):
        """ Récupération des valeurs pour les lignes de facture de révision des lignes de contrat groupées """
        total = 0
        vals = {}
        invoice_type = 'out_invoice'
        for contract_line in self:
            lines = contract_line.generate_revision_line(invoicing_date)
            if not lines:
                continue
            for line in lines:
                total += line['quantity'] * line['price_unit']
            vals[contract_line.name] = lines
        if total < 0:
            invoice_type = 'out_refund'
            for key, lines in vals.iteritems():
                for line in lines:
                    line['quantity'] = line['quantity'] * -1
        return_vals = []
        for key, lines in vals.iteritems():
            for line in lines:
                return_vals.append((0, 0, line))
        return invoice_type, return_vals

    @api.multi
    def _revision_avenant(self):
        """ Créer la facture de révision d'un avenant """
        if not self.revision_avenant:
            return
        lines = []
        date = self.date_avenant
        period = self.contract_id.period_ids.filtered(lambda p: p.date_start <= date <= p.date_end)
        if not period:
            return
        for product_line in self.contract_product_ids.filtered('previous_product_id'):
            line = product_line.previous_product_id
            qty_invoiced = line._get_quantity_invoiced_on_period(period)

            nbr_invoices = len(line.invoice_line_ids.mapped('invoice_id')
                                   .filtered(lambda i: period.date_start <= i.date_invoice <= period.date_end))
            search = bool(nbr_invoices)
            while search:
                line = line.previous_product_id
                new_qty = len(line.invoice_line_ids.mapped('invoice_id')
                                  .filtered(lambda i: period.date_start <= i.date_invoice <= period.date_end))
                search = bool(new_qty)
                nbr_invoices += new_qty

            qty_to_invoice = nbr_invoices * product_line.qty_to_invoice
            qty_to_invoice = qty_to_invoice - qty_invoiced
            if not qty_to_invoice:
                continue
            vals = product_line._prepare_invoice_line()
            vals['quantity'] = qty_to_invoice
            lines.append(vals)
        if lines:
            invoice_vals = self.contract_id._prepare_invoice(do_raise=False)
            invoice_vals['date_invoice'] = date
            invoice_vals['invoice_line_ids'] = [(0, 0, line) for line in lines]
            self.env['account.invoice'].create(invoice_vals)
        return lines

    @api.multi
    def remove_services(self):
        """ Suppression des services dont la date suivante est supérieure à la date de fin de la ligne de contrat """
        for line in self:
            if not line.date_contract_end:
                continue
            services = line.service_ids.filtered(lambda s: not s.intervention_ids)
            if services:
                services.unlink()


class OfContractProduct(models.Model):
    _name = 'of.contract.product'
    _order = 'sequence'

    sequence = fields.Integer(string=u"Séquence", default=10, help=u"Séquence")
    line_id = fields.Many2one(
        comodel_name='of.contract.line', string="Ligne de contrat", required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Article", required=True)
    price_unit = fields.Float(string="Prix unitaire")
    price_unit_prec = fields.Float(string=u"Prix unitaire précédent")
    purchase_price = fields.Float(string=u"Coût")
    purchase_price_prec = fields.Float(string=u"Coût précédent")
    next_purchase_price = fields.Float(string=u"Prochain coût", compute='_compute_amount')
    year_purchase_price = fields.Float(string=u"Coût annuel", compute='_compute_amount')
    name = fields.Text(string='Description', required=True)
    quantity = fields.Float(string=u"Qté", default=1.0)
    uom_id = fields.Many2one('product.uom', string=u'Unité de mesure')
    company_currency_id = fields.Many2one(
        'res.currency', related='line_id.company_currency_id', string="Company Currency", readonly=True)
    amount_subtotal = fields.Monetary(
        string="Sous-total", compute='_compute_amount', currency_field='company_currency_id',
        digits=dp.get_precision('Account'), store=True
    )
    amount_taxes = fields.Monetary(
        string="Taxes ", compute='_compute_amount', currency_field='company_currency_id', store=True)
    amount_total = fields.Monetary(
        string="Prochain Total", compute='_compute_amount', currency_field='company_currency_id', store=True)
    discount = fields.Float(
        string='Remise (%)', digits=dp.get_precision('Discount'), help=u'Remise appliquée pour les factures')
    invoice_line_ids = fields.One2many(
        'account.invoice.line', 'of_contract_product_id', string="Lignes de factures", readonly=True)
    tax_ids = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '=', 'sale')], copy=True)
    account_analytic_id = fields.Many2one('account.analytic.account', string=u"Compte analytique")
    qty_per_period = fields.Float(string=u"Qté facturée par année", compute="_compute_quantities", store=True)
    qty_to_invoice = fields.Float(string=u"Qté a facturer", compute="_compute_quantities", store=True)
    qty_invoiced = fields.Float(string=u"Qté facturée", compute="_compute_qty_invoiced", store=True)
    previous_product_id = fields.Many2one(
        comodel_name='of.contract.product', string="Produit sur ligne d'origine", copy=False)
    next_product_id = fields.Many2one(
        comodel_name='of.contract.product', string="Produit sur ligne d'avenant", compute="_compute_next_product_id")
    date_indexed = fields.Date(string=u"Dernière indexation")
    date_indexed_prec = fields.Date(string=u"Précédent indexation")
    year_subtotal = fields.Float(
        string="Sous-total annuel", compute='_compute_amount', digits=dp.get_precision('Account'), store=True)
    year_taxes = fields.Monetary(
        string="Taxes annuelles", compute='_compute_amount', currency_field='company_currency_id', store=True)
    year_total = fields.Monetary(
        string="Total annuel", compute='_compute_amount', currency_field='company_currency_id', store=True)

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'qty_to_invoice', 'company_currency_id',
                 'line_id', 'line_id.is_invoiceable', 'purchase_price', 'line_id.address_id', 'product_id')
    def _compute_amount(self):
        """ Calcul des montants pour la ligne d'article """
        # c_product pour contract_product
        for c_product in self:
            price = c_product.price_unit * (1 - (c_product.discount or 0.0) / 100.0)
            # For a single month
            taxes = c_product.tax_ids.compute_all(price, c_product.company_currency_id, c_product.qty_to_invoice,
                                             product=c_product.product_id, partner=c_product.line_id.address_id)
            c_product.amount_taxes = taxes['total_included'] - taxes['total_excluded']
            c_product.amount_total = taxes['total_included']
            c_product.amount_subtotal = taxes['total_excluded']
            c_product.next_purchase_price = c_product.purchase_price * c_product.qty_to_invoice
            # For a year
            taxes = c_product.tax_ids.compute_all(price, c_product.company_currency_id, c_product.quantity,
                                             product=c_product.product_id, partner=c_product.line_id.address_id)
            c_product.year_taxes = taxes['total_included'] - taxes['total_excluded']
            c_product.year_total = taxes['total_included']
            c_product.year_subtotal = taxes['total_excluded']
            c_product.year_purchase_price = c_product.purchase_price * c_product.quantity

    @api.multi
    def _compute_tax_id(self):
        """ Calcul des taxes pour la ligne d'article """
        for line_product in self:
            fpos = line_product.line_id.fiscal_position_id or \
                   line_product.line_id.partner_id.property_account_position_id
            taxes = line_product.line_id.company_id._of_filter_taxes(line_product.product_id.taxes_id)
            line_product.tax_ids = fpos.map_tax(taxes, line_product.product_id,
                                                line_product.line_id.address_id) if fpos else taxes

    @api.depends('invoice_line_ids', 'invoice_line_ids.quantity',
                 'invoice_line_ids.invoice_id',
                 'invoice_line_ids.invoice_id.state',
                 'invoice_line_ids.of_contract_supposed_date',
                 'line_id',
                 'line_id.next_date',
                 'line_id.current_period_id',
                 'line_id.state',
                 'previous_product_id')
    def _compute_qty_invoiced(self):
        """ Calcul des qtés facturés sur la période courante de la ligne de contrat """
        for product_line in self:
            if not product_line.invoice_line_ids and not product_line.previous_product_id:
                continue
            date_range = product_line.line_id.current_period_id
            lines = product_line.invoice_line_ids\
                                .filtered(lambda l: l.of_contract_supposed_date and
                                          date_range.date_start <= l.of_contract_supposed_date <= date_range.date_end)
            qty_out_invoice = sum(lines.filtered(lambda il: il.invoice_id.type == 'out_invoice').mapped('quantity'))
            qty_out_refund = sum(lines.filtered(lambda il: il.invoice_id.type == 'out_refund').mapped('quantity'))
            qty_invoiced = qty_out_invoice - qty_out_refund
            avenant_de = product_line.previous_product_id
            if avenant_de and avenant_de.line_id.current_period_id.id == date_range.id:
                old_lines = avenant_de.invoice_line_ids\
                                      .filtered(lambda l: l.of_contract_supposed_date and
                                                date_range.date_start <= l.of_contract_supposed_date <= date_range.date_end)
                old_qty_out_invoice = sum(old_lines.filtered(
                        lambda il: il.invoice_id.type == 'out_invoice').mapped('quantity'))
                old_qty_out_refund = sum(old_lines.filtered(
                        lambda il: il.invoice_id.type == 'out_refund').mapped('quantity'))
                qty_invoiced += old_qty_out_invoice - old_qty_out_refund
            product_line.qty_invoiced = qty_invoiced

    @api.depends('quantity', 'line_id', 'line_id.nbr_interv', 'line_id.next_date', 'line_id.state', 'qty_invoiced',
                 'line_id.current_period_id',
                 'line_id.frequency_type',
                 'line_id.recurring_invoicing_payment_id.code',
                 'line_id.revision',
                 'line_id.contract_id.period',
                 'invoice_line_ids',
                 'invoice_line_ids.quantity', 'invoice_line_ids.invoice_id',
                 'invoice_line_ids.invoice_id.state')
    def _compute_quantities(self):
        """ Calcul de la qté à facturer """
        for product_line in self:
            line = product_line.line_id
            qty_per_period = product_line.quantity
            product_line.qty_per_period = qty_per_period
            last_day = product_line.line_id.current_period_id.date_end
            frequency_type = line.frequency_type
            qty_to_invoice = 0
            if last_day and line.recurring_invoicing_payment_id.code == 'post-paid' and \
               last_day == line.next_date and line.revision == 'last_day':
                qty_to_invoice = round(product_line.qty_per_period - product_line.qty_invoiced, 3)
            else:
                if frequency_type == 'month':
                    qty_to_invoice = qty_per_period / (line.contract_id.period or 12)
                elif frequency_type == 'trimester':
                    qty_to_invoice = qty_per_period / 4.0
                elif frequency_type == 'semester':
                    qty_to_invoice = qty_per_period / 2.0
                elif frequency_type == 'year':
                    qty_to_invoice = qty_per_period
                elif frequency_type == 'date':
                    qty_to_invoice = 1.0
            product_line.qty_to_invoice = qty_to_invoice

    def _compute_next_product_id(self):
        """ Calcul la ligne d'article présente sur une ligne de contrat avenant """
        product_line_obj = self.env['of.contract.product']
        for product_line in self:
            product_line.next_product_id = product_line_obj.search([('previous_product_id', '=', product_line.id)],
                                                                   limit=1)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            product = self.product_id
            name = product.name_get()[0][1]
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name
            self.price_unit = product.list_price
            self.purchase_price = product.get_cost()
            self.uom_id = product.uom_id
            self._compute_tax_id()

    @api.multi
    def _prepare_invoice_line(self):
        """ Renvoi un dictionnaire de valeur pour la facturation de l'article """
        self.ensure_one()
        invoice_line_new = self.env['account.invoice.line'].new({
            'product_id'   : self.product_id.id,
            'name': self.name,
            })
        type = 'out_invoice'
        product = self.product_id
        fpos = self.line_id.fiscal_position_id
        company = self.line_id.contract_id.company_id
        account = self.env['account.invoice.line'].get_invoice_line_account(type, product, fpos, company)
        for tax in self.tax_ids:
            account = tax.map_account(account)
        invoice_line_new._onchange_product_id()
        invoice_line_vals = invoice_line_new._convert_to_write(invoice_line_new._cache)
        # Get other invoice line values from product onchange
        name = u"%s" % (self.name or '')
        name += u"\n%s%s" % (self.line_id.address_id.name or u'',
                             self.line_id.partner_code_magasin and
                             (u", Magasin n°%s" % self.line_id.partner_code_magasin) or u'')
        invoice_line_vals.update({
            'quantity': self.qty_to_invoice,
            'uom_id': self.product_id.uom_id.id,
            'discount': self.discount,
            'of_contract_product_id': self.id,
            'invoice_line_tax_ids': [(6, 0, [tax.id for tax in self.tax_ids])],
            'name': name,
            'price_unit': self.price_unit,
            'of_contract_supposed_date': self.line_id.next_date,
            'account_id': account.id,
            'account_analytic_id': self.account_analytic_id and self.account_analytic_id.id,
        })

        return invoice_line_vals

    @api.multi
    def _get_quantity_invoiced_on_period(self, period):
        """ Permet de récupérer la qté facturée sur une période donnée """
        self.ensure_one()
        base_line = self
        date_start = period.date_start
        date_end = period.date_end
        qty = sum(base_line.invoice_line_ids
                           .filtered(lambda l: l.invoice_id.state != 'cancel'
                                               and date_start <= l.of_contract_supposed_date <= date_end)
                           .mapped('quantity'))
        search = bool(qty)
        while search:
            base_line = base_line.previous_product_id
            new_qty = sum(base_line.invoice_line_ids
                                   .filtered(lambda l: l.invoice_id.state != 'cancel'
                                                       and date_start <= l.of_contract_supposed_date <= date_end)
                                   .mapped('quantity'))
            search = bool(new_qty)
            qty += new_qty
        return qty

    @api.multi
    def _get_quantity_done_on_period(self, period):
        """ Permet de récupérer la qté réalisée sur une période donnée """
        self.ensure_one()
        base_line = self
        date_start = period.date_start
        date_end = period.date_end
        qty = len(base_line.line_id.intervention_ids.filtered(lambda i: date_start <= i.date_date <= date_end
                                                                        and i.state == 'done'))
        search = bool(qty)
        while search:
            base_line = base_line.previous_product_id
            new_qty = len(base_line.line_id.intervention_ids.filtered(lambda i: date_start <= i.date_date <= date_end
                                                                                and i.state == 'done'))
            search = bool(new_qty)
            qty += new_qty
        return qty * self.quantity


class OfContractPeriod(models.Model):
    _name = 'of.contract.period'
    _order = 'number'

    name = fields.Char(string=u"Nom de la période", compute="_compute_name")
    contract_id = fields.Many2one(comodel_name='of.contract', string="Contrat", required=True, ondelete='cascade')
    number = fields.Integer(string=u"Période n°", required=True)
    date_start = fields.Date(string=u"Date de début", required=True)
    date_end = fields.Date(string=u"Date de fin", required=True)
    has_invoices = fields.Boolean(string=u"À une facture sur la période", compute="_compute_has_invoices", store=True)

    @api.depends('date_start', 'date_end')
    def _compute_name(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for period in self:
            if not period.date_start or not period.date_end:
                continue
            period.name = u"Période %s - %s" % (format_date(period.date_start, lang), format_date(period.date_end, lang))

    @api.depends('contract_id', 'contract_id.invoice_ids', 'date_start', 'date_end')
    def _compute_has_invoices(self):
        for period in self:
            if not period.date_start or not period.date_end or not period.contract_id:
                continue
            invoice = period.contract_id.invoice_ids\
                                        .filtered(lambda i: i.state != 'cancel' and
                                                            period.date_start <= i.date_invoice <= period.date_end)
            if invoice:
                period.has_invoices = True


