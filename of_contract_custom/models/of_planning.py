# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from odoo.addons.of_utils.models.of_utils import format_date
from dateutil.relativedelta import relativedelta


class OfPlanningPlannification(models.AbstractModel):
    _name = 'of.planning.plannification'

    # @api.model_cr_context
    # def _auto_init(self):
    #     cr = self._cr
    #
    #
    #     res = super(OfPlanningPlannification, self)._auto_init()
    #     return res

    nbr_interv = fields.Integer(
        required=False, compute='_compute_nbr_interv', string="Nombre de visites",
        help=u"Nombre de RDV d'interventions dans l'année", store=True)
    interv_frequency_nbr = fields.Integer(string=u"Interval de fréquence (RDV)", required=True)
    interv_frequency = fields.Selection(selection=[
        ('month', 'Mois'),
        ('year', 'Ans'),
        ], string=u"Type de fréquence (RDV)", required=True)
    mois_reference_ids = fields.Many2many(comodel_name='of.mois', string=u"Mois de visite", required=True)
    intervention_template_id = fields.Many2one(
        comodel_name='of.planning.intervention.template', string=u"Modèle d'intervention")
    tache_id = fields.Many2one(comodel_name='of.planning.tache', string=u"Tâche", required=True)

    @api.multi
    def _generate_services(self):
        """Fonction à implémenter pour générer les interventions à programmer"""
        raise NotImplementedError("A class inheriting from this one must implement '_generate_services' function")

    @api.depends('interv_frequency_nbr', 'interv_frequency', 'mois_reference_ids')
    def _compute_nbr_interv(self):
        for contract in self:
            if contract.interv_frequency == 'month':
                months = len(contract.mois_reference_ids)
                contract.nbr_interv = months * contract.interv_frequency_nbr
            elif contract.interv_frequency == 'year':
                contract.nbr_interv = contract.interv_frequency_nbr

    @api.onchange('intervention_template_id')
    def _onchange_intervention_template_id(self):
        if self.intervention_template_id:
            self.tache_id = self.intervention_template_id.tache_id


class OfService(models.Model):
    _name = 'of.service'
    _inherit = ['of.service', 'mail.thread']

    @api.model
    def _init_number(self):
        """
        Màj T2427 : ajout du champ number dans les DI, initialisation du champ.
        """
        service_obj = self.with_context(active_test=False)
        services = service_obj.search([('base_state', '=', 'calculated'), ('number', '=', False)])
        services._affect_number()

    @api.model
    def _domain_employee_ids(self):
        return ['|', ('of_est_intervenant', '=', True), ('of_est_commercial', '=', True)]

    type_id = fields.Many2one(
        comodel_name='of.service.type', string="Type", required=True,)
    of_categorie_id = fields.Many2one('of.project.issue.categorie', string=u"Catégorie", ondelete='restrict')
    of_canal_id = fields.Many2one('of.project.issue.canal', string=u"Canal", ondelete='restrict')
    partner_code_magasin = fields.Char(string="Code magasin", related="partner_id.of_code_magasin", readonly=True)
    # partner_id.category_id est un M2M
    partner_tag_ids = fields.Many2many(string=u"Étiquettes client", related='partner_id.category_id', readonly=True)
    supplier_id = fields.Many2one(comodel_name='res.partner', string="Prestataire", domain="[('supplier','=',True)]")
    contract_id = fields.Many2one(comodel_name='of.contract', string="Contrat")
    contract_line_id = fields.Many2one(
        comodel_name='of.contract.line', string="Ligne de contrat",
        domain="['|','|',('contract_id','=',contract_id),('partner_id','=',partner_id),('address_id','=',address_id)]"
    )
    order_id = fields.Many2one(
        domain="['|', ('partner_id', 'child_of', partner_id), ('partner_id', 'parent_of', partner_id)]")
    saleorder_ids = fields.One2many(comodel_name='sale.order', compute='_compute_saleorder_ids', string=u"Ventes")
    sale_invoice_ids = fields.One2many(
        comodel_name='account.invoice', compute='_compute_sale_invoice_ids', string=u"Factures de ventes")
    saleorder_count = fields.Integer(string=u"# Ventes", compute='_compute_saleorder_ids')
    sale_invoice_count = fields.Integer(string=u"# Factures de ventes", compute='_compute_sale_invoice_ids')
    historique_interv_ids = fields.Many2many(
        string=u"Historique des interventions", comodel_name='of.planning.intervention',
        column1='of.service', column2='of.planning.intervention', relation='of_service_historique_interv_rel',
        compute='_compute_historique_interv_ids',
        help=u"Historique des RDVs du parc installé. Si pas de parc installé, historique de l'adresse")
    template_id = fields.Many2one(comodel_name='of.planning.intervention.template', string=u"Modèle d'intervention")
    number = fields.Char(String=u"Numéro", copy=False)
    titre = fields.Char(string=u"Titre")
    priority = fields.Selection(
        [
            ('0', 'Low'),
            ('1', 'Normal'),
            ('2', 'High')
        ], string=u"Priorité", index=True, default='0')
    spec_date = fields.Char(string="Date", compute="_compute_spec_date")
    user_id = fields.Many2one(comodel_name='res.users', string="Utilisateur", default=lambda r:r.env.user)
    kanban_step_id = fields.Many2one(
        comodel_name='of.service.stage', string=u"Étapes kanban", group_expand='_read_group_stage_ids',
        domain="[('type_ids','=',type_id)]"
    )
    state = fields.Selection(track_visibility='onchange')
    parc_type_garantie = fields.Selection(related='parc_installe_id.type_garantie')
    contract_message = fields.Char(string="Infos SAV du contrat", compute="_compute_contract_message")
    employee_ids = fields.Many2many(
        comodel_name='hr.employee', string="Intervenants", domain=lambda self: self._domain_employee_ids()
    )
    payer_mode = fields.Selection([
        ('client', u"Client"),
        ('retailer', u"Revendeur"),
        ('manufacturer', u"Fabricant"),
    ], string=u"Payeur")
    last_attachment_id = fields.Many2one(
        comodel_name='ir.attachment', string=u"Dernier rapport", compute="_compute_last_attachment_id"
    )
    recurrence = fields.Boolean(string=u"Est récurrente", default=False)
    transformed = fields.Boolean(string=u"Transfomé en contrat")
    line_ids = fields.One2many(
        comodel_name='of.service.line', inverse_name='service_id', string=u"Lignes de facturation")
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string=u"Position fiscale",
        domain="[('tax_ids.tax_src_id.type_tax_use','=','sale')]")
    currency_id = fields.Many2one(
        comodel_name='res.currency', string=u"Currency", readonly=True, related='company_id.currency_id')

    price_subtotal = fields.Monetary(compute='_compute_amount', string=u"Sous-total HT", readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string=u"Taxes", readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string=u"Sous-total TTC", readonly=True, store=True)

    # @api.depends

    @api.depends('line_ids', 'line_ids.saleorder_line_id')
    def _compute_saleorder_ids(self):
        for service in self:
            service.saleorder_ids = service.line_ids.mapped('saleorder_line_id').mapped('order_id')
            service.saleorder_count = len(service.saleorder_ids)

    @api.depends('line_ids', 'line_ids.saleorder_line_id.invoice_lines')
    def _compute_sale_invoice_ids(self):
        for service in self:
            service.sale_invoice_ids = service.line_ids.mapped('saleorder_line_id').mapped('invoice_lines')\
                .mapped('invoice_id')
            service.sale_invoice_count = len(service.sale_invoice_ids)

    @api.depends('parc_installe_id.intervention_ids', 'address_id.intervention_address_ids',
                 'partner_id.intervention_address_ids')
    def _compute_historique_interv_ids(self):
        for service in self:
            if service.parc_installe_id:
                service.historique_interv_ids = service.parc_installe_id.intervention_ids
            elif service.address_id:
                service.historique_interv_ids = service.address_id.intervention_address_ids
            else:
                service.historique_interv_ids = service.partner_id.intervention_address_ids

    @api.depends()
    def _compute_spec_date(self):
        lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
        for service in self:
            interventions = service.intervention_ids.filtered(lambda i: i.state not in ('cancel', 'postponed'))
            if service.state == 'done' and interventions:
                service.spec_date = u"Réalisée le %s" % format_date(service.intervention_ids[-1].date_date, lang)
            elif interventions:
                service.spec_date = u"Prévue le %s" % format_date(service.intervention_ids[-1].date_date, lang)
            else:
                service.spec_date = u"Prévue entre %s et %s" % (format_date(service.date_next, lang), format_date(service.date_fin, lang))

    @api.depends('contract_line_id', 'contract_line_id.use_sav', 'type_id')
    def _compute_contract_message(self):
        sav_type = self.env.ref('of_contract_custom.of_contract_custom_type_sav', raise_if_not_found=False)
        if sav_type:
            for service in self:
                if service.type_id.id == sav_type.id and service.contract_line_id.use_sav:
                    count = service.contract_line_id.remaining_sav
                    service.contract_message = "%s SAV restant(s) pour cette ligne de contrat" % count
                elif service.type_id.id == sav_type.id and service.contract_line_id:
                    service.contract_message = "Cette ligne de contrat n'utilise pas l'option SAV"

    @api.depends()
    def _compute_last_attachment_id(self):
        """ Récupère le rapport 'Fiche d'intervention' du dernier RDV ayant la fiche d'intervention dans ses PJ"""
        attachment_obj = self.env['ir.attachment']
        for service in self:
            interventions = service.intervention_ids.filtered(lambda i: i.state not in ('cancel', 'postponed'))
            if interventions:
                for i in xrange(1, len(service.intervention_ids) + 1):
                    current_interv = service.intervention_ids[-i]
                    attachment = attachment_obj.search([('res_model', '=', 'of.planning.intervention'),
                                                        ('res_id', '=', current_interv.id),
                                                        ('of_intervention_report', '=', True)])
                    if attachment:
                        service.last_attachment_id = attachment[-1]
                        break

    @api.depends('line_ids', 'line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.price_total')
    def _compute_amount(self):
        for intervention in self:
            intervention.price_subtotal = sum(intervention.line_ids.mapped('price_subtotal'))
            intervention.price_tax = sum(intervention.line_ids.mapped('price_tax'))
            intervention.price_total = sum(intervention.line_ids.mapped('price_total'))

    # @api.onchange

    @api.onchange('template_id')
    def onchange_template_id(self):
        service_line_obj = self.env['of.service.line']
        template = self.template_id
        if self.base_state == "draft" and template:
            if template.tache_id:
                self.tache_id = template.tache_id
            if not self.fiscal_position_id:
                self.fiscal_position_id = template.fiscal_position_id
            if self.line_ids:
                new_lines = self.line_ids
            else:
                new_lines = service_line_obj
            for line in template.line_ids:
                data = line.get_intervention_line_values()
                data['service_id'] = self.id
                new_lines += service_line_obj.new(data)
            new_lines.compute_taxes()
            self.line_ids = new_lines

    @api.onchange('tache_id')
    def _onchange_tache_id(self):
        super(OfService, self)._onchange_tache_id()
        if self.tache_id:
            if self.tache_id.fiscal_position_id and not self.fiscal_position_id:
                self.fiscal_position_id = self.tache_id.fiscal_position_id
            if self.tache_id.product_id:
                self.line_ids.new({
                    'service__id': self.id,
                    'product_id': self.tache_id.product_id.id,
                    'qty': 1,
                    'price_unit': self.tache_id.product_id.lst_price,
                    'name': self.tache_id.product_id.name,
                })
                self.line_ids.compute_taxes()

    @api.onchange('address_id', 'tache_id')
    def _onchange_address_id(self):
        super(OfService, self)._onchange_address_id()
        if self.address_id:
            if self.address_id.of_prestataire_id:
                self.supplier_id = self.address_id.of_prestataire_id

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        if self.contract_id and self.contract_id.partner_id:
            self.partner_id = self.contract_id.partner_id

    @api.onchange('contract_line_id')
    def onchange_contract_line_id(self):
        if self.contract_line_id and self.contract_line_id.address_id:
            self.address_id = self.contract_line_id.address_id
            self.parc_installe_id = self.contract_line_id.parc_installe_id

    @api.onchange('type_id')
    def onchange_type_id(self):
        if self.type_id and self.type_id.kanban_ids:
            self.kanban_step_id = self.type_id.kanban_ids[0]

    @api.onchange('recurrence')
    def _onchange_recurrent(self):
        if self.recurrence:
            self.contract_id = False
            self.contract_line_id = False

    @api.onchange('contract_id', 'contract_line_id')
    def _onchange_contract_id(self):
        if self.contract_id or self.contract_line_id:
            self.recurrence = False

    # Héritages

    @api.multi
    def write(self, vals):
        res = super(OfService, self).write(vals)
        if vals.get('base_state') == 'calculated':
            self._affect_number()
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """
        Surcharge de la fonction pour afficher toutes les étapes existantes sur vue kanban
        """
        return stages.search([], order=order)

    # Actions

    @api.multi
    def action_view_saleorder(self):
        if self.ensure_one():
            return {
                'name': u"Commandes client",
                'view_mode': 'tree,kanban,form',
                'res_model': 'sale.order',
                'res_id': self.saleorder_ids.ids,
                'domain': "[('id', 'in', %s)]" % self.saleorder_ids.ids,
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def action_view_sale_invoice(self):
        if self.ensure_one():
            return {
                'name': u"Factures client",
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.invoice',
                'res_id': self.sale_invoice_ids.ids,
                'domain': "[('id', 'in', %s)]" % self.sale_invoice_ids.ids,
                'type': 'ir.actions.act_window',
            }

    @api.model
    def make_sale_order(self):
        self.ensure_one()

        # Ne pas créer de commande si pas de lignes
        if not self.line_ids:
            return self.env['of.popup.wizard'].popup_return(
                message=u"Cette demande d'intervention n'a aucune ligne.")

        # Ne pas créer de commande si toutes les lignes sont déjà associées à une commande
        if not self.line_ids.filtered(lambda l: not l.saleorder_line_id):
            return self.env['of.popup.wizard'].popup_return(
                message=u"Toutes les lignes sont déjà associées à une commande de vente.")

        # Ne pas créer de commande si toutes les lignes sont déjà associées à une commande
        if not self.fiscal_position_id:
            return self.env['of.popup.wizard'].popup_return(
                message=u"Veuillez renseigner une position fiscale.")

        res = {
              'name': u"Devis",
              'view_mode': 'form',
              'res_model': 'sale.order',
              'type': 'ir.actions.act_window',
              'target': 'current',
        }
        sale_obj = self.env['sale.order']
        so_line_obj = self.env['sale.order.line']
        # utilisation de new() pour trigger les onchanges facilement
        sale_order_new = sale_obj.new({
            'partner_id': self.partner_id.id,
            'origin': self.number,
        })
        sale_order_new.onchange_partner_id()
        sale_order_new.update({'fiscal_position_id': self.fiscal_position_id.id})
        order_values = sale_order_new._convert_to_write(sale_order_new._cache)
        sale_order = sale_obj.create(order_values)
        lines_to_create = []
        # Récupération des lignes de commandes
        for line in self.line_ids.filtered(lambda l: not l.saleorder_line_id):
            line_vals = line.prepare_so_line_vals(sale_order)
            lines_to_create.append((0, 0, line_vals))
        sale_order.write({'order_line': lines_to_create})
        # Connecter les lignes à leur ligne de commande correspondante
        for line in self.line_ids.filtered(lambda l: not l.saleorder_line_id):
            line.saleorder_line_id = so_line_obj.search([('of_service_line_id', '=', line.id)], limit=1)
        # Renvoyer la commande créée
        res['res_id'] = sale_order.id

        return res

    @api.multi
    def get_action_view_intervention_context(self, action_context={}):
        context_vals = {}
        if self.contract_line_id:
            context_vals['default_contract_line_id'] = self.contract_line_id.id
            context_vals['default_employee_ids'] = [(6, 0, [emp.id for emp in self.employee_ids])]
        if self.fiscal_position_id:
            context_vals['default_fiscal_position_id'] = self.fiscal_position_id.id
        if self.template_id:
            context_vals['default_template_id'] = self.template_id.id
        if self.line_ids:
            # Générer les lignes ici ne fonctionnait pas, on signale donc dans le contexte qu'il faudra les générer.
            # Elles seront ensuite générées dans le onchange_service_id
            context_vals['of_import_service_lines'] = True
        action_context.update(context_vals)
        return super(OfService, self).get_action_view_intervention_context(action_context)

    @api.multi
    def action_view_contract(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.action_contract').read()[0]
        action['domain'] = [('id', '=', self.contract_id.id)]
        return action

    @api.multi
    def button_open_of_planning_intervention(self):
        self.ensure_one()
        action = self.env.ref('of_contract_custom.of_contract_custom_open_interventions').read()[0]
        interventions = self.intervention_ids
        if len(interventions) > 1:
            action['context'] = {'search_default_service_id': self.id}
        elif len(interventions) == 1:
            action['views'] = [(self.env.ref('of_planning.of_planning_intervention_view_form').id, 'form')]
            action['res_id'] = interventions.ids[0]
        else:
            action = self.env['of.popup.wizard'].popup_return(message=u"Aucun RDV d'intervention lié.")
        return action

    @api.multi
    def action_service_send(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'of.service',
            'default_res_id': self.ids[0],
            'default_composition_mode': 'comment'
        })
        try:
            template_id = self.env.ref('of_contract_custom.email_template_of_service').id
            ctx['default_template_id'] = template_id
            ctx['default_use_template'] = bool(template_id)
        except ValueError:
            pass
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def print_intervention_report(self):
        if self.intervention_ids:
            return self.env['report'].get_action(self.intervention_ids, 'of_planning.of_planning_fiche_intervention_report_template')
        else:
            return self.env['of.popup.wizard'].popup_return(message=u"Aucun RDV d'intervention lié.")

    # Autres

    @api.multi
    def _affect_number(self):
        """ Affectation du numéro """
        for service in self:
            if service.base_state == 'calculated' and not service.number:
                number = self.env['ir.sequence'].next_by_code('of.service')
                service.write({'number': number})

    @api.model
    def of_get_report_name(self, docs):
        return "Demande d'intervention"

    @api.model
    def of_get_report_number(self, docs):
        if len(docs) == 1:
            return docs.number
        return ""

    @api.model
    def of_get_report_date(self, docs):
        if len(docs) == 1:
            lang = self.env['res.lang']._lang_get(self.env.lang or 'fr_FR')
            return "%s " % format_date(docs.date_next, lang)
        return ""

    @api.multi
    def transform_to_contract(self):
        payment_type = self.env.ref('of_contract_custom.of_contract_recurring_invoicing_payment_post-paid')
        contract_obj = self.env['of.contract']
        contract_line_obj = self.env['of.contract.line']
        for service in self:
            if not service.recurrence or service.transformed or not service.address_id:
                continue
            first_of_the_month = fields.Date.from_string(fields.Date.today()) + relativedelta(day=1)
            first_of_the_month = fields.Date.to_string(first_of_the_month)
            vals_contract = {
                'contract_type': 'simple',
                'reference': service.partner_id.ref or 'Contrat',
                'partner_id': service.partner_id.id,
                'recurring_rule_type': 'month',
                'recurring_invoicing_payment_id': payment_type.id,
                'renewal': True,
                'date_start': first_of_the_month > service.date_next and first_of_the_month or service.date_next,
                }
            vals_line = {
                'address_id': service.address_id.id,
                'frequency_type': 'month',
                'recurring_invoicing_payment_id': payment_type.id,
                'parc_installe_id': service.parc_installe_id.id,
                'tache_id': service.tache_id.id,
                'mois_reference_ids': [(4, mois.id) for mois in service.mois_ids],
                }
            if service.recurring_rule_type == 'monthly':
                nbr_interv = 12.0 / float(service.recurring_interval)
                if nbr_interv.is_integer() and (nbr_interv/float(len(service.mois_ids))).is_integer():
                    interv_per_month = nbr_interv/len(service.mois_ids)
                    vals_line['interv_frequency_nbr'] = interv_per_month
                    vals_line['interv_frequency'] = 'month'
                else:
                    vals_line['interv_frequency_nbr'] = int(nbr_interv)
                    vals_line['interv_frequency'] = 'year'
            else:
                vals_line['interv_frequency_nbr'] = 1
                vals_line['interv_frequency'] = 'year'
            print vals_contract
            new_contract = contract_obj.create(vals_contract)
            vals_line['contract_id'] = new_contract.id
            contract_line_obj.create(vals_line)
            service.transformed = True


class OfServiceLine(models.Model):
    _name = 'of.service.line'

    service_id = fields.Many2one(
        comodel_name='of.service', string=u"Demande d'intervention", required=True, ondelete='cascade')
    saleorder_line_id = fields.Many2one(
        comodel_name='sale.order.line', string=u"Ligne de vente",
        help=u"Utilisé pour savoir si une commande a été générée pour cette ligne.")
    sol_number = fields.Char(string=u"CC", related='saleorder_line_id.order_id.name', readonly=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner', related='service_id.partner_id', readonly=True)
    company_id = fields.Many2one(
        comodel_name='res.company', related='service_id.company_id', string=u'Société', readonly=True)
    currency_id = fields.Many2one(
        comodel_name='res.currency', string=u"Currency", readonly=True, related='company_id.currency_id')

    product_id = fields.Many2one(comodel_name='product.product', string=u"Article")
    price_unit = fields.Monetary(
        string=u"Prix unitaire", digits=dp.get_precision('Product Price'), default=0.0, currency_field='currency_id'
    )
    qty = fields.Float(string=u"Qté", digits=dp.get_precision('Product Unit of Measure'))
    name = fields.Text(string=u"Description")
    taxe_ids = fields.Many2many(comodel_name='account.tax', string=u"TVA")
    discount = fields.Float(string=u"Remise (%)", digits=dp.get_precision('Discount'), default=0.0)

    price_subtotal = fields.Monetary(compute='_compute_amount', string=u"Sous-total HT", readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string=u"Taxes", readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string=u"Sous-total TTC", readonly=True, store=True)

    @api.depends('qty', 'price_unit', 'taxe_ids')
    def _compute_amount(self):
        u"""
        Calcule le montant de la ligne.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxe_ids.compute_all(price, line.currency_id, line.qty,
                                              product=line.product_id, partner=line.service_id.address_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.onchange('product_id')
    def _onchange_product(self):
        product = self.product_id
        self.qty = 1
        self.price_unit = product.lst_price
        if product:
            name = product.name_get()[0][1]
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name
        else:
            self.name = ''
        if product:
            self.compute_taxes()

    @api.multi
    def compute_taxes(self):
        for line in self:
            product = line.product_id
            partner = line.partner_id
            fiscal_position = line.service_id.fiscal_position_id
            taxes = product.taxes_id
            if partner.company_id:
                taxes = taxes.filtered(lambda r: r.company_id == partner.company_id)
            if fiscal_position:
                taxes = fiscal_position.map_tax(taxes, product, partner)
            line.taxe_ids = taxes

    @api.multi
    def prepare_intervention_line_vals(self):
        self.ensure_one()
        return {
            'product_id': self.product_id and self.product_id.id,
            'price_unit': self.price_unit,
            'qty': self.qty,
            'name': self.name,
            'taxe_ids': [(6, 0, self.taxe_ids and self.taxe_ids._ids or [])],
            'discount': self.discount,
        }

    @api.multi
    def prepare_so_line_vals(self, order):
        self.ensure_one()
        sale_line_obj = self.env['sale.order.line']
        # utilisation de new pour permettre les onchange
        order_line_new = sale_line_obj.new({
            'product_id': self.product_id.id,
            'order_id': order.id,
            'of_service_line_id': self.id,
        })
        order_line_new.product_id_change()
        order_line_new.product_uom_change()
        order_line_new.update({'product_uom_qty': self.qty})
        return order_line_new._convert_to_write(order_line_new._cache)


class OfServiceType(models.Model):
    _name = 'of.service.type'

    name = fields.Char(string="Type de service")
    kanban_ids = fields.Many2many(comodel_name='of.service.stage', string=u"Étapes autorisées")


class OfServiceStage(models.Model):
    _name = 'of.service.stage'
    _order = 'sequence'

    name = fields.Char(string=u"Nom de l'étape")
    sequence = fields.Integer(string=u"Séquence")
    type_ids = fields.Many2many(comodel_name='of.service.type', string=u"Types autorisés")


class OfPlanningInterventionTemplate(models.Model):
    _inherit = 'of.planning.intervention.template'

    type_id = fields.Many2one(
        comodel_name='of.service.type', string="Type")

    @api.multi
    def name_get(self):
        """Permet dans un RDV d'intervention de proposer les modèles d'un type différent entre parenthèses"""
        type_id = self._context.get('type_prio_id')
        type = type_id and self.env['of.service.type'].browse(type_id) or False
        result = []
        for template in self:
            meme_type = template.type_id and template.type_id.id == type_id if type else True
            result.append((template.id, "%s%s%s" % ('' if meme_type else '(',
                                                    template.name,
                                                    '' if meme_type else ')')))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permet dans un RDV d'intervention de proposer en priorité les modèles de même type"""
        if self._context.get('type_prio_id'):
            type_id = self._context.get('type_prio_id')
            args = args or []
            res = super(OfPlanningInterventionTemplate, self).name_search(
                name,
                args + [['type_id', '=', type_id], ['type_id', '!=', False]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(OfPlanningInterventionTemplate, self).name_search(
                name,
                args + [['type_id', '=', False]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(OfPlanningInterventionTemplate, self).name_search(
                name,
                args + [['type_id', '!=', type_id], ['type_id', '!=', False]],
                operator,
                limit) or []
            return res
        return super(OfPlanningInterventionTemplate, self).name_search(name, args, operator, limit)


class OfPlanningIntervention(models.Model):
    _inherit = 'of.planning.intervention'

    @api.model_cr_context
    def _auto_init(self):
        u"""
        Initialiser le champ type_id en fonction du type_id de la DI
        """
        cr = self._cr
        cr.execute("SELECT * FROM information_schema.columns "
                   "WHERE table_name = 'of_planning_intervention' AND column_name = 'type_id'")
        exists = bool(cr.fetchall())
        res = super(OfPlanningIntervention, self)._auto_init()
        if not exists:
            cr.execute("UPDATE of_planning_intervention AS interv SET type_id = service.type_id "
                       "FROM of_service AS service WHERE interv.service_id = service.id")
            cr.commit()
        return res

    type_id = fields.Many2one(
        comodel_name='of.service.type', string="Type")

    contract_line_id = fields.Many2one(
        comodel_name='of.contract.line', string="Ligne de contrat",
        domain="service_id and [('service_ids','=',service_id)] or "
               "address_id and [('address_id','=',address_id)] or "
               "[]")
    contract_id = fields.Many2one(
            comodel_name='of.contract', string="Contrat",
            domain="service_id and [('service_ids','=',service_id)] or "
                   "partner_id and [('partner_id','=',partner_id)] or "
                   "address_id and [('partner_id','=',address_id)] or "
                   "[]")
    partner_code_magasin = fields.Char(string="Code magasin", related="partner_id.of_code_magasin", readonly=True)

    @api.onchange('contract_line_id')
    def _onchange_contract_line_id(self):
        if self.contract_line_id:
            self.contract_id = self.contract_line_id.contract_id
            self.address_id = self.contract_line_id.address_id or self.contract_line_id.partner_id

    @api.onchange('service_id')
    def _onchange_service_id(self):
        super(OfPlanningIntervention, self)._onchange_service_id()
        if self.service_id:
            self.contract_line_id = self.service_id.contract_line_id
            self.contract_id = self.service_id.contract_id
            if self.service_id.order_id:
                self.order_id = self.service_id.order_id
            if self.service_id.type_id:
                # Quand le RDV a une DI associée, le type est en readonly dans le XML et donc n'est pas écrit
                # l'affectation de type n'est que cosmétique ici
                self.type_id = self.service_id.type_id.id
            if self._context.get('of_import_service_lines'):
                self.fiscal_position_id = self.service_id.fiscal_position_id
                line_vals = [(5,)]
                for line in self.service_id.line_ids:
                    line_vals.append((0, 0, line.prepare_intervention_line_vals()))
                self.line_ids = line_vals

    @api.multi
    def write(self, vals):
        # Quand le RDV a une DI associée, le type est en readonly dans le XML et donc n'est pas écrit
        # On affecte donc le type en sous-marin
        if vals.get('service_id'):
            service = self.env['of.service'].browse(vals['service_id'])
            if service.type_id:
                vals['type_id'] = service.type_id.id
        return super(OfPlanningIntervention, self).write(vals)

    @api.model
    def create(self, vals):
        # Quand le RDV a une DI associée, le type est en readonly dans le XML et donc n'est pas écrit
        # On affecte donc le type en sous-marin
        if vals.get('service_id'):
            service = self.env['of.service'].browse(vals['service_id'])
            if service.type_id:
                vals['type_id'] = service.type_id.id
        return super(OfPlanningIntervention, self).create(vals)


class Report(models.Model):
    _inherit = "report"

    @api.model
    def get_pdf(self, docids, report_name, html=None, data=None):
        if report_name == 'of_planning.of_planning_fiche_intervention_report_template':
            self = self.with_context(copy_to_di=True, fiche_intervention=True)
        return super(Report, self).get_pdf(docids, report_name, html=html, data=data)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    of_intervention_report = fields.Boolean(string="Fiche d'intervention")

    def create(self, vals):
        if self._context.get('fiche_intervention'):
            vals['of_intervention_report'] = True
        attachment = super(IrAttachment, self).create(vals)
        if self._context.get('copy_to_di') and vals.get('res_model', '') == 'of.planning.intervention' \
           and vals.get('res_id') and isinstance(vals['res_id'], int):
            interv = self.env['of.planning.intervention'].browse(vals['res_id'])
            if interv.service_id:
                new_vals = vals.copy()
                new_vals['res_model'] = 'of.service'
                new_vals['res_id'] = interv.service_id.id
                self.env['ir.attachment'].create(new_vals)
        return attachment
