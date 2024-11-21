# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    of_booking_terms_file = fields.Binary(
        string="Planning booking - PDF file for General Terms and Conditions",
        filename="of_booking_terms_filename",
        compute="_compute_of_booking_terms_file",
    )
    of_booking_terms_filename = fields.Char(
        string="Planning booking - PDF file name for General Terms and Conditions",
        compute="_compute_of_booking_terms_file",
    )

    def _compute_of_booking_terms_file(self):
        company_dependent = self.env.user.company_id.sudo().of_booking_specific
        for website in self:
            if company_dependent:
                company = self.env.user.company_id.sudo()
            else:
                company = website.company_id.sudo()
            website.of_booking_terms_file = company.of_booking_terms_file
            website.of_booking_terms_filename = company.of_booking_terms_filename
