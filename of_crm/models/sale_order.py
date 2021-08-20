# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'of.crm.stage.auto.update']

    @api.model
    def _auto_init(self):
        """
        À l'installation du module :
            - les commandes avec l'ancien état 'Devis' sont passés au nouvel état 'Devis'
            - le nouveau champ 'Devis envoyé' est passé à vrai pour les commandes avec l'ancien état 'Devis envoyé'
        """
        cr = self._cr
        new_workflow = False
        new_canvasser_field = False
        if self._auto:
            cr.execute(
                "SELECT * "
                "FROM information_schema.columns "
                "WHERE table_name = '%s' "
                "AND column_name = 'of_sent_quotation'" % self._table)
            new_workflow = not bool(cr.fetchall())

            cr.execute(
                "SELECT * "
                "FROM information_schema.columns "
                "WHERE table_name = '%s' "
                "AND column_name = 'of_canvasser_id'" % self._table)
            new_canvasser_field = not bool(cr.fetchall())

        res = super(SaleOrder, self)._auto_init()

        if new_workflow:
            cr.execute("UPDATE %s "
                       "SET of_sent_quotation = True "
                       "WHERE state = 'sent'" % self._table)
            cr.execute("UPDATE %s "
                       "SET state = 'sent' "
                       "WHERE state = 'draft'" % self._table)

        if new_canvasser_field:
            cr.execute(
                "UPDATE %s SO "
                "SET of_canvasser_id = COALESCE(CL.of_prospecteur_id, RP.of_prospecteur_id, NULL) "
                "FROM %s SO2 "
                "INNER JOIN res_partner RP ON RP.id = SO2.partner_id "
                "LEFT JOIN crm_lead CL ON (CL.id = SO2.opportunity_id) "
                "WHERE SO.id = SO2.id" % (self._table, self._table))

        return res

    @api.model
    def _default_state(self):
        start_state = self.env['ir.values'].get_default('sale.config.settings', 'of_sale_order_start_state')
        if start_state == 'quotation':
            return 'sent'
        else:
            return 'draft'

    of_referred_id = fields.Many2one(
        'res.partner', string=u"Apporté par", help="Nom de l'apporteur d'affaire", copy=False)
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', domain="[('type', '=', 'opportunity')]", copy=False)
    campaign_id = fields.Many2one(
        'utm.campaign', 'Campaign', copy=False,
        help="This is a name that helps you keep track of your different campaign efforts Ex: Fall_Drive, "
             "Christmas_Special")
    source_id = fields.Many2one(
        'utm.source', 'Source', copy=False,
        help="This is the source of the link Ex:Search Engine, another domain,or name of email list")
    medium_id = fields.Many2one(
        'utm.medium', 'Medium', copy=False, help="This is the method of delivery.Ex: Postcard, Email, or Banner Ad",
        oldname='channel_id')
    state = fields.Selection([
        ('draft', u'Estimation'),
        ('sent', u'Devis'),
        ('sale', u'Bon de commande'),
        ('done', u'Verrouillé'),
        ('cancel', u'Annulé'),
    ], default=_default_state)
    of_sent_quotation = fields.Boolean(string=u"Devis envoyé")
    of_canvasser_id = fields.Many2one(comodel_name='res.users', string=u"Prospecteur")

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()
        if self.partner_id.of_prospecteur_id:
            self.of_canvasser_id = self.partner_id.of_prospecteur_id

    @api.onchange('opportunity_id')
    def onchange_opportunity(self):
        if self.opportunity_id:
            self.of_referred_id = self.opportunity_id.of_referred_id
            self.campaign_id = self.opportunity_id.campaign_id
            self.medium_id = self.opportunity_id.medium_id
            self.source_id = self.opportunity_id.source_id
            self.team_id = self.opportunity_id.team_id
            if self.opportunity_id.user_id and self.state != 'sale':
                self.user_id = self.opportunity_id.user_id
            if self.opportunity_id.of_prospecteur_id and self.state != 'sale':
                self.of_canvasser_id = self.opportunity_id.of_prospecteur_id

    @api.model
    def create(self, vals):
        start_state = self.env['ir.values'].get_default('sale.config.settings', 'of_sale_order_start_state')
        if start_state == 'quotation':
            if vals.get('state', 'draft') == 'draft':
                vals.update(state='sent')
        else:
            vals.update(state='draft')
        order = super(SaleOrder, self).create(vals)
        if vals.get('opportunity_id'):
            lead = self.env['crm.lead'].browse(vals['opportunity_id'])
            # on connecte la commande aux RDV plutôt que l'inverse car plus facile de toucher un M2O qu'un O2M
            lead.of_intervention_ids.write({'order_id': order.id})
        return order

    @api.multi
    def write(self, values):
        start_state = self.env['ir.values'].get_default('sale.config.settings', 'of_sale_order_start_state')
        if values.get('state', False) == 'draft' and start_state == 'quotation':
            values.update(state='sent')
        res =  super(SaleOrder, self).write(values)
        if values.get('opportunity_id') and len(self) == 1:
            lead = self.env['crm.lead'].browse(values['opportunity_id'])
            # on connecte la commande aux RDV plutôt que l'inverse car plus facile de toucher un M2O qu'un O2M
            lead.of_intervention_ids.write({'order_id': self.id})

        return res

    @api.multi
    def action_confirm(self):
        """
        Un prospect devient signé sur confirmation de commande
        """
        res = super(SaleOrder, self).action_confirm()
        partners = self.env['res.partner']
        for order in self:
            if order.partner_id.of_customer_state == 'lead' and order.partner_id not in partners:
                partners += order.partner_id
        partners.write({'of_customer_state': 'customer'})
        return res

    @api.multi
    def action_confirm_estimation(self):
        return self.filtered(lambda s: s.state == 'draft').write({'state': 'sent'})

    @api.multi
    def print_quotation(self):
        # on redéfinit la fonction standard pour court-circuiter le changement d'état
        return self.env['report'].get_action(self, 'sale.report_saleorder')

    @api.multi
    def action_quotation_send(self):
        # on redéfinit la fonction standard pour court-circuiter le changement d'état
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('sale', 'email_template_edi_sale')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'of_mark_so_as_sent': True,
            'default_composition_mode': 'comment',
            'custom_layout': "sale.mail_template_data_notification_email_sale_order"
        })
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
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['of_canvasser_id'] = self.of_canvasser_id.id
        return invoice_vals


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _auto_init(self):
        cr = self._cr
        new_canvasser_field = False
        if self._auto:
            cr.execute(
                "SELECT * "
                "FROM information_schema.columns "
                "WHERE table_name = '%s' "
                "AND column_name = 'of_canvasser_id'" % self._table)
            new_canvasser_field = not bool(cr.fetchall())

        res = super(AccountInvoice, self)._auto_init()

        if new_canvasser_field:
            cr.execute(
                "UPDATE %s AI "
                "SET of_canvasser_id = COALESCE(SO.of_canvasser_id, RP.of_prospecteur_id, NULL) "
                "FROM  %s AI2 "
                "INNER JOIN res_partner RP ON RP.id = AI2.partner_id "
                "LEFT JOIN sale_order SO ON (SO.name = AI2.origin) "
                "WHERE AI.id = AI2.id" % (self._table, self._table))

        return res

    of_canvasser_id = fields.Many2one(
        comodel_name='res.users', string=u"Prospecteur", readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user)

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        partners = self.env['res.partner']
        for invoice in self:
            if invoice.partner_id.of_customer_state == 'lead' and invoice.partner_id not in partners and \
                    invoice.partner_id.customer:
                partners += invoice.partner_id
        partners.write({'of_customer_state': 'customer'})
        return res


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    @api.model
    def _auto_init(self):
        super(SaleConfiguration, self)._auto_init()
        if not self.env['ir.values'].get_default('sale.config.settings', 'of_sale_order_start_state'):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_sale_order_start_state', 'quotation')

    @api.model
    def _init_sale_order_state_group(self):
        group_quotation_sale_order_state = self.env.ref('of_crm.group_quotation_sale_order_state')
        group_estimation_sale_order_state = self.env.ref('of_crm.group_estimation_sale_order_state')
        group_user = self.env.ref('base.group_user')
        if group_quotation_sale_order_state not in group_user.implied_ids and \
                group_estimation_sale_order_state not in group_user.implied_ids:
            self.env.ref('base.group_public').write({'implied_ids': [(4, group_quotation_sale_order_state.id)]})
            self.env.ref('base.group_portal').write({'implied_ids': [(4, group_quotation_sale_order_state.id)]})
            self.env.ref('base.group_user').write({'implied_ids': [(4, group_quotation_sale_order_state.id)]})

    group_estimation_sale_order_state = fields.Boolean(
        string=u"Commandes créés à l'étape Estimation",
        implied_group='of_crm.group_estimation_sale_order_state',
        group='base.group_portal,base.group_user,base.group_public')
    group_quotation_sale_order_state = fields.Boolean(
        string=u"Commandes créés à l'étape Devis",
        implied_group='of_crm.group_quotation_sale_order_state',
        group='base.group_portal,base.group_user,base.group_public')
    of_sale_order_start_state = fields.Selection(
        selection=[('estimation', u"Les commandes sont créées à l'étape initiale Estimation"),
                   ('quotation', u"Les commandes sont créées à l'étape initiale Devis")],
        string=u"(OF) État de départ des commandes",
        default='quotation',
        required=True)

    @api.multi
    def set_of_sale_order_start_state_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'of_sale_order_start_state', self.of_sale_order_start_state)

    @api.onchange('of_sale_order_start_state')
    def _onchange_of_sale_order_start_state(self):
        if self.of_sale_order_start_state == "estimation":
            self.update({
                'group_estimation_sale_order_state': True,
                'group_quotation_sale_order_state': False,
            })
        else:
            self.update({
                'group_estimation_sale_order_state': False,
                'group_quotation_sale_order_state': True,
            })


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'sale.order' and self._context.get('default_res_id') and \
                self._context.get('of_mark_so_as_sent'):
            order = self.env['sale.order'].browse([self._context['default_res_id']])
            order.of_sent_quotation = True
            self = self.with_context(mail_post_autofollow=True)
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
