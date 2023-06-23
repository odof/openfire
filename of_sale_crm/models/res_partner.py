# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'utm.mixin']

    @api.model_cr_context
    def _auto_init(self):
        """
        Synchronisation du champ 'of_customer_state' entre les contacts enfants physiques et leur parent
        :todo: Trouver quoi faire de cette fonction - est-elle utile ? Complémentaire du hoot d'intallation ?
            S'il faut la lancer à chaque mise à jour, cel avient peut-être d'une anomalie dans le reste du code
        """
        res = super(ResPartner, self)._auto_init()
        cr = self._cr
        cr.execute(
            """ UPDATE  res_partner         RP
                SET     of_customer_state   = RP1.of_customer_state
                FROM    res_partner         RP1
                WHERE   RP.parent_id        IS NOT NULL
                AND     RP.is_company       = False
                AND     RP1.id              = RP.parent_id"""
        )
        return res

    of_customer_state = fields.Selection(
        selection=[('lead', "Prospect"), ('customer', "Client signé"), ('other', "Autre")],
        string="État",
        default='other',
        required=True,
        help="""
Champ uniquement utile pour les partenaires clients.
Un client est considéré comme prospect tant qu'il n'a ni commande confirmée ni facture validée.
Ce champ se met à jour automatiquement sur confirmation de commande et sur validation de facture""",
    )
    # :todo: à déplacer dans of_sale
    # Les champs suivants ne sont pas utilisés, mais permettent un affichage en vue liste des contacts
    #   grâce au list editor.
    of_quotations_count = fields.Integer(compute='_compute_of_quotations_count', string='Nb devis')
    of_sale_order_quot_count = fields.Integer(compute='_compute_of_sale_order_quot_count', string='Nb dev+cmd')

    def _compute_of_quotations_count(self):
        self.of_compute_sale_orders_count('of_quotations_count', [('state', 'in', ['draft', 'sent'])])

    def _compute_of_sale_order_quot_count(self):
        self.of_compute_sale_orders_count('of_sale_order_quot_count', [('state', '!=', ['cancel'])])

    def _compute_sale_order_count(self):
        self.of_compute_sale_orders_count('sale_order_count', [('state', 'in', ['sale', 'done'])])

    def of_compute_sale_orders_count(self, field, state_domain=[]):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        all_partners.read(['parent_id'])

        sale_order_groups = self.env['sale.order'].read_group(
            domain=[('partner_id', 'in', all_partners.ids)] + state_domain,
            fields=['partner_id'],
            groupby=['partner_id'],
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

    @api.model_create_multi
    def create(self, vals_list):
        """
        On creation of a partner, will set of_customer_state field.
        """
        for vals in vals_list:
            parent_id = vals.get('parent_id', False)
            if parent_id and not vals.get('is_company', False):
                parent = self.browse(parent_id)
                vals['of_customer_state'] = parent.of_customer_state
            else:
                if not vals.get('customer'):
                    # partner is not a customer -> set to 'other'
                    vals['of_customer_state'] = 'other'
                elif vals.get('of_customer_state', 'other') == 'other':
                    # partner is a customer -> defaults to 'lead'
                    vals['of_customer_state'] = 'lead'
        return super().create(vals_list)

    def write(self, vals):
        """Permet la synchronisation du champ of_customer_state pour tout les contacts liés"""
        if 'of_customer_state' in vals and self._context.get('customer_state_recursion', True):
            for partner in self:
                parent = partner
                while parent.parent_id:
                    parent = parent.parent_id
                partners = self.search([('id', 'child_of', parent.id), ('is_company', '=', False)])
                partners.with_context(customer_state_recursion=False).of_customer_state = vals['of_customer_state']
        return super().write(vals)
