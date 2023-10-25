# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Low'),
    ('2', 'High'),
    ('3', 'Very High'),
]


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    customer_view = fields.Boolean(string="Customer/Vendor view")
    of_referred_id = fields.Many2one(
        comodel_name='res.partner', string="Brought by", help="Name of business contributor", copy=False
    )
    opportunity_id = fields.Many2one(
        comodel_name='crm.lead', string="Opportunity", domain="[('type', '=', 'opportunity')]", copy=False
    )
    campaign_id = fields.Many2one(
        comodel_name='utm.campaign',
        string="Campaign",
        copy=False,
        help="This is a name that helps you keep track of your different campaign efforts Ex: Fall_Drive, "
        "Christmas_Special",
    )
    source_id = fields.Many2one(
        comodel_name='utm.source',
        string='Source',
        copy=False,
        help="This is the source of the link Ex:Search Engine, another domain,or name of email list",
    )
    medium_id = fields.Many2one(
        comodel_name='utm.medium',
        string='Medium',
        copy=False,
        help="This is the method of delivery.Ex: Postcard, Email, or Banner Ad",
    )
    state = fields.Selection(  # override selection values
        selection=[
            ('draft', "Estimate"),
            ('sent', "Quotation"),
            ('sale', "Sale Order"),
            ('done', "Locked"),
            ('cancel', "Canceled"),
        ],
        default='draft',
    )
    of_sent_quotation = fields.Boolean(string="Quotation sent", copy=False)
    of_canvasser_id = fields.Many2one(comodel_name='res.users', string="Canvasser")
    of_crm_activity_ids = fields.One2many(
        comodel_name='of.crm.activity',
        inverse_name='order_id',
        string='Activities',
        copy=True,
        context={'active_test': False},
    )
    of_activities_state = fields.Selection(
        selection=[('in_progress', 'In progress'), ('late', 'Late'), ('done', 'Done'), ('canceled', 'Canceled')],
        string='Status of activities',
        store=True,
    )
    # Follow-up fields
    of_sale_followup_tag_ids = fields.Many2many(
        comodel_name='of.sale.followup.tag',
        relation='sale_order_followup_tag_rel',
        column1='order_id',
        column2='tag_id',
        string='Follow-up tags',
    )
    of_priority = fields.Selection(selection=AVAILABLE_PRIORITIES, string='Priority', index=True, default='0')
    of_notes = fields.Text(string='Follow-up notes')
    of_info = fields.Text(string='Info')
    of_reference_laying_date = fields.Date(string='Reference laying date')
    of_force_laying_date = fields.Boolean(string='Force laying date')
    of_manual_laying_date = fields.Date(string='Manual laying date')
    of_laying_week = fields.Char(string="Laying week")
    of_main_product_brand_id = fields.Many2one(
        comodel_name='of.product.brand',
        string="Brand of the main product",
    )

    def action_button_confirm_estimate(self):
        raise NotImplementedError('Nope. This is only the phase 1 of migration to v16.')
