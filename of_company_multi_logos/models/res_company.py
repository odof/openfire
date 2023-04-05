# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_logo_ids = fields.Many2many(
        comodel_name='of.company.multi.logos',
        relation='res_company_of_logo_rel',
        column1='company_id',
        column2='logo_id',
        string="Logos",
    )
    of_use_logo_footer = fields.Boolean(
        string="Footer logos",
        compute='_compute_of_use_logo_footer',
        store=True,
        help="This company uses logos to be positioned just above the footer",
    )

    @api.depends('of_logo_ids', 'of_logo_ids.logo_position')
    def _compute_of_use_logo_footer(self):
        for company in self:
            company.of_use_logo_footer = bool(
                company.of_logo_ids.filtered(
                    lambda s: s.logo_position in ('footer', 'footer_right_corner', 'footer_left_corner')
                )
            )

    def _compute_field_value(self, field):
        super()._compute_field_value(field)
        # Ensure that the paperformat is set to the correct value after the compute
        if field.name == 'of_use_logo_footer':
            for company in self:
                # Utiliser le format de papier spécial
                if company.of_use_logo_footer:
                    paperformat = self.env.ref('of_company_multi_logos.paperformat_euro_of_logo_footer')
                # Utiliser le format de papier standard
                else:
                    paperformat = self.env.ref('base.paperformat_euro')
                company.write({'paperformat_id': paperformat.id})

    def _get_footer_logos(self):
        self.ensure_one()
        return self.of_logo_ids.filtered(lambda s: s.logo_position == 'footer')

    def _get_footer_corner_logos(self):
        self.ensure_one()
        return self.of_logo_ids.filtered(lambda s: s.logo_position in ('footer_right_corner', 'footer_left_corner'))

    def _get_footer_right_corner_logos(self):
        self.ensure_one()
        return self._get_footer_corner_logos().filtered(lambda s: s.logo_position == 'footer_right_corner')

    def _get_footer_left_corner_logos(self):
        self.ensure_one()
        return self._get_footer_corner_logos().filtered(lambda s: s.logo_position == 'footer_left_corner')

    def _get_company_logo(self, name):
        """Get the logo from a given name"""
        return next((logos.logo for logos in self.of_logo_ids if logos.name == name), False)
