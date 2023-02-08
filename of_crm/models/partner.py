# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from odoo import models, fields, api


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'utm.mixin']

    @api.model_cr_context
    def _auto_init(self):
        """
        Synchronisation du champ 'of_customer_state' entre les contacts enfants physiques et leur parent
        """
        res = super(ResPartner, self)._auto_init()
        cr = self._cr
        cr.execute("""  UPDATE  res_partner         RP
                        SET     of_customer_state   = RP1.of_customer_state
                        FROM    res_partner         RP1
                        WHERE   RP.parent_id        IS NOT NULL
                        AND     RP.is_company       = False
                        AND     RP1.id              = RP.parent_id""")
        return res

    def _get_default_user_id(self):
        return self._uid

    user_id = fields.Many2one('res.users', default=lambda s: s._get_default_user_id())
    of_customer_state = fields.Selection([
        ('lead', u'Prospect'),
        ('customer', u'Client signé'),
        ('other', u'Autre')], string=u"État", default='other', required=True, help=u"""
Champ uniquement utile pour les partenaires clients.
Un client est considéré comme prospect tant qu'il n'a ni commande confirmée ni facture validée.
Ce champ se met à jour automatiquement sur confirmation de commande et sur validation de facture""")

    @api.model
    def _init_prospects(self):
        """
        Cette fonction a pour but d'initialiser le champ of_customer_state.
        Pour les partenaires non clients (champ 'customer' à False): of_customer_state = 'other'
        Pour les partenaires client:
            si un partenaire (ou son parent le cas échéant) a au moins une vente ou
                une facturation: of_customer_state = 'customer'
            sinon: of_customer_state = 'lead'
        On s'occupe des enfants après s'être occupé de leur parent.
        """
        partner_obj = self.with_context(active_test=False)
        # all partners
        partners = partner_obj.search([])
        # (ré)initialisation du champ à 'other' pour tous les partenaires
        partners.write({'of_customer_state': 'other'})

        customers = partner_obj.search([('customer', '=', True)])
        customers._compute_sale_order_count()  # needed (because store=False computed field?)
        to_lead = self.env['res.partner']
        to_customer = self.env['res.partner']
        len_customers = len(customers)

        todo = partner_obj.search(
            [('customer', '=', True), '|', ('parent_id', '=', False), ('parent_id.customer', '=', False)])
        while todo:
            partner = todo[0]
            todo -= todo[0]
            if partner.sale_order_count == 0 and partner.total_invoiced == 0:
                if partner.parent_id and partner.parent_id in to_customer:
                    to_customer += partner
                else:
                    to_lead += partner
            else:
                to_customer += partner

            # search pour récupérer les éventuels enfants archivés
            # potentially inactive children
            todo += partner_obj.search([('parent_id', '=', partner.id), ('customer', '=', True)])
        to_lead.write({'of_customer_state': 'lead'})
        to_customer.write({'of_customer_state': 'customer'})
        len_done = len(to_lead) + len(to_customer)
        if len_customers != len_done:  # not all partners have been processed
            _logger.warning(u"fonction '_init_prospects': incohérence. Clients à traiter %d - %d Clients traités" %
                            (len_customers, len_done))
        else:
            _logger.info(u"fonction '_init_prospects': %d clients ont été traités" % len_done)

    meeting_ids = fields.Many2many('calendar.event', 'calendar_event_res_partner_rel', string='Meetings')
    of_prospecteur_id = fields.Many2one("res.users", string="Prospecteur", oldname='of_prospecteur')
    # Les champs suivants ne sont pas utilisés, mais permettent un affichage en vue liste des contacts
    #   grâce au list editor.
    of_quotations_count = fields.Integer(compute='_compute_of_quotations_count', string='Nb devis')
    of_sale_order_quot_count = fields.Integer(compute='_compute_of_sale_order_quot_count', string='Nb dev+cmd')

    of_lead_campaign_id = fields.Many2one(
        comodel_name='utm.campaign', string=u"Campagne", compute='_compute_of_lead_utm')
    of_lead_medium_id = fields.Many2one(comodel_name='utm.medium', string=u"Canal", compute='_compute_of_lead_utm')
    of_lead_source_id = fields.Many2one(comodel_name='utm.source', string=u"Origine", compute='_compute_of_lead_utm')
    of_is_lead_warn = fields.Boolean(string="Leads warning")

    def _compute_of_quotations_count(self):
        self.of_compute_sale_orders_count('of_quotations_count', [('state', 'in', ['draft', 'sent'])])

    def _compute_of_sale_order_quot_count(self):
        self.of_compute_sale_orders_count('of_sale_order_quot_count', [('state', '!=', ['cancel'])])

    def _compute_sale_order_count(self):
        self.of_compute_sale_orders_count('sale_order_count', [('state', 'in', ['sale', 'done'])])

    @api.depends('opportunity_ids')
    def _compute_of_lead_utm(self):
        for partner in self:
            if partner.opportunity_ids:
                partner.of_lead_campaign_id = partner.opportunity_ids[0].campaign_id.id
                partner.of_lead_source_id = partner.opportunity_ids[0].source_id.id
                partner.of_lead_medium_id = partner.opportunity_ids[0].medium_id.id
            else:
                partner.of_lead_campaign_id = False
                partner.of_lead_source_id = False
                partner.of_lead_medium_id = False

    @api.depends('of_is_lead_warn')
    def _compute_of_is_warn(self):
        has_warn = self.filtered(lambda p: p.of_is_lead_warn)
        for partner in has_warn:
            partner.of_is_warn = True
        partners_left = self - has_warn
        super(ResPartner, partners_left)._compute_of_is_warn()

    def of_compute_sale_orders_count(self, field, state_domain=[]):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        sale_order_groups = self.env['sale.order'].read_group(
            domain=[('partner_id', 'in', all_partners.ids)] + state_domain,
            fields=['partner_id'], groupby=['partner_id']
        )
        for group in sale_order_groups:
            partner = self.browse(group['partner_id'][0])
            while partner:
                if partner in self:
                    partner[field] += group['partner_id_count']
                partner = partner.parent_id

    @api.onchange('customer')
    def _onchange_customer(self):
        for partner in self:
            if partner.customer and partner.of_customer_state == 'other':
                partner.of_customer_state = 'lead'
            elif not partner.customer and partner.of_customer_state != 'other':
                partner.of_customer_state = 'other'

    @api.model
    def create(self, vals):
        """
        On creation of a partner, will set of_customer_state field.
        """
        parent_id = vals.get('parent_id', False)
        if parent_id and not vals.get('is_company', False):
            parent = self.browse(parent_id)
            vals.update(of_customer_state=parent.of_customer_state)
        else:
            if not vals.get('customer'):  # partner is not a customer -> set to 'other'
                vals['of_customer_state'] = 'other'
            elif vals.get('of_customer_state', 'other') == 'other':  # partner is a customer -> defaults to 'lead'
                vals['of_customer_state'] = 'lead'

        partner = super(ResPartner, self).create(vals)

        return partner

    @api.multi
    def write(self, vals):
        """ Permet la synchronisation du champ of_customer_state pour tout les contacts liés
        """
        if 'of_customer_state' in vals and self._context.get('customer_state_recursion', True):
            for partner in self:
                parent = partner
                while parent.parent_id:
                    parent = parent.parent_id
                partners = self.search([('id', 'child_of', parent.id), ('is_company', '=', False)])
                partners.with_context(customer_state_recursion=False).\
                    write({'of_customer_state': vals['of_customer_state']})
        return super(ResPartner, self).write(vals)

    def get_crm_partner_name(self):
        res = self.name
        return res


class ResPartnerCategory(models.Model):
    _inherit = 'res.partner.category'

    def get_crm_tags_data(self):
        result = self.name
        return result


class ResCompany(models.Model):
    _inherit = 'res.company'

    crm_suivi = fields.Boolean(string="Actions Co suivies", default=True)
    crm_suivi_notes = fields.Boolean(string="avec les notes", default=False)

    @api.onchange('crm_suivi')
    def _onchange_crm_suivi(self):
        for company in self:
            if not company.crm_suivi:
                company.crm_suivi_notes = False

    @api.onchange('crm_suivi_notes')
    def _onchange_crm_suivi_notes(self):
        for company in self:
            if company.crm_suivi_notes:
                company.crm_suivi = True
