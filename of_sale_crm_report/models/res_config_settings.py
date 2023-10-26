# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_funnel_conversion1 = fields.Boolean(
        string="Display of the qualitative conversion funnel",
        implied_group='of_sale_crm_report.group_funnel_conversion1',
        group='sales_team.group_sale_salesman',
    )
    of_display_funnel_conversion1 = fields.Boolean(
        string="(OF) Display of the qualitative conversion funnel",
        config_parameter='of.sale.crm.report.display_funnel_conversion1',
    )
    group_funnel_conversion2 = fields.Boolean(
        string="Display of the quantitative conversion funnel",
        implied_group='of_sale_crm_report.group_funnel_conversion2',
        group='sales_team.group_sale_salesman',
    )
    of_display_funnel_conversion2 = fields.Boolean(
        string="(OF) Display of the quantitative conversion funnel",
        config_parameter='of.sale.crm.report.display_funnel_conversion2',
    )

    @api.onchange('of_display_funnel_conversion1')
    def _onchange_of_display_funnel_conversion1(self):
        self.group_funnel_conversion1 = self.of_display_funnel_conversion1

    @api.onchange('of_display_funnel_conversion2')
    def _onchange_of_display_funnel_conversion2(self):
        self.group_funnel_conversion2 = self.of_display_funnel_conversion2
