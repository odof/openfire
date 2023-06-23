# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


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
        if (
            group_quotation_sale_order_state not in group_user.implied_ids
            and group_estimation_sale_order_state not in group_user.implied_ids
        ):
            self.env.ref('base.group_public').write({'implied_ids': [(4, group_quotation_sale_order_state.id)]})
            self.env.ref('base.group_portal').write({'implied_ids': [(4, group_quotation_sale_order_state.id)]})
            self.env.ref('base.group_user').write({'implied_ids': [(4, group_quotation_sale_order_state.id)]})

    @api.model
    def _init_crm_funnel_conversion_group(self):
        group_funnel_conversion1 = self.env.ref('of_crm.group_funnel_conversion1')
        if not self.env['ir.values'].search(
            [('name', '=', 'of_display_funnel_conversion1'), ('model', '=', 'sale.config.settings')]
        ):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_display_funnel_conversion1', True)
            self.env.ref('sales_team.group_sale_salesman').write({'implied_ids': [(4, group_funnel_conversion1.id)]})
        group_funnel_conversion2 = self.env.ref('of_crm.group_funnel_conversion2')
        if not self.env['ir.values'].search(
            [('name', '=', 'of_display_funnel_conversion2'), ('model', '=', 'sale.config.settings')]
        ):
            self.env['ir.values'].sudo().set_default('sale.config.settings', 'of_display_funnel_conversion2', True)
            self.env.ref('sales_team.group_sale_salesman').write({'implied_ids': [(4, group_funnel_conversion2.id)]})

    group_estimation_sale_order_state = fields.Boolean(
        string="Commandes créés à l'étape Estimation",
        implied_group='of_crm.group_estimation_sale_order_state',
        group='base.group_portal,base.group_user,base.group_public',
    )
    group_quotation_sale_order_state = fields.Boolean(
        string="Commandes créés à l'étape Devis",
        implied_group='of_crm.group_quotation_sale_order_state',
        group='base.group_user',
    )
    of_sale_order_start_state = fields.Selection(
        selection=[
            ('estimation', "Les commandes sont créées à l'étape initiale Estimation"),
            ('quotation', "Les commandes sont créées à l'étape initiale Devis"),
        ],
        string="(OF) État de départ des commandes",
        default='quotation',
        required=True,
    )
    of_lost_opportunity_stage_id = fields.Many2one(
        comodel_name='crm.stage',
        string="(OF) Étape perdue des opportunités",
        help="Permet d'indiquer quelle est l'étape associée à la perte d'opportunité pour des besoins d'analyse",
    )
    group_funnel_conversion1 = fields.Boolean(
        string="Affichage du tunnel de conversion qualitatif",
        implied_group='of_crm.group_funnel_conversion1',
        group='sales_team.group_sale_salesman',
    )
    of_display_funnel_conversion1 = fields.Boolean(
        string="(OF) Affichage du tunnel de conversion qualitatif", default=True
    )
    group_funnel_conversion2 = fields.Boolean(
        string="Affichage du tunnel de conversion quantitatif",
        implied_group='of_crm.group_funnel_conversion2',
        group='sales_team.group_sale_salesman',
    )
    of_display_funnel_conversion2 = fields.Boolean(
        string="(OF) Affichage du tunnel de conversion quantitatif", default=True
    )

    @api.multi
    def set_of_sale_order_start_state_defaults(self):
        return (
            self.env['ir.values']
            .sudo()
            .set_default('sale.config.settings', 'of_sale_order_start_state', self.of_sale_order_start_state)
        )

    @api.onchange('of_sale_order_start_state')
    def _onchange_of_sale_order_start_state(self):
        if self.of_sale_order_start_state == "estimation":
            self.update(
                {
                    'group_estimation_sale_order_state': True,
                    'group_quotation_sale_order_state': False,
                }
            )
        else:
            self.update(
                {
                    'group_estimation_sale_order_state': False,
                    'group_quotation_sale_order_state': True,
                }
            )

    @api.multi
    def set_of_lost_opportunity_stage_id_defaults(self):
        return (
            self.env['ir.values']
            .sudo()
            .set_default('sale.config.settings', 'of_lost_opportunity_stage_id', self.of_lost_opportunity_stage_id.id)
        )

    @api.multi
    def set_of_display_funnel_conversion1(self):
        return (
            self.env['ir.values']
            .sudo()
            .set_default('sale.config.settings', 'of_display_funnel_conversion1', self.of_display_funnel_conversion1)
        )

    @api.onchange('of_display_funnel_conversion1')
    def _onchange_of_display_funnel_conversion1(self):
        if self.of_display_funnel_conversion1:
            self.update({'group_funnel_conversion1': True})
        else:
            self.update({'group_funnel_conversion1': False})

    @api.multi
    def set_of_display_funnel_conversion2(self):
        return (
            self.env['ir.values']
            .sudo()
            .set_default('sale.config.settings', 'of_display_funnel_conversion2', self.of_display_funnel_conversion2)
        )

    @api.onchange('of_display_funnel_conversion2')
    def _onchange_of_display_funnel_conversion2(self):
        if self.of_display_funnel_conversion2:
            self.update({'group_funnel_conversion2': True})
        else:
            self.update({'group_funnel_conversion2': False})
