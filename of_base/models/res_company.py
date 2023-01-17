# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, api, fields, SUPERUSER_ID, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    of_legal_form = fields.Char(string="Legal form")
    of_capital = fields.Char(string="Social capital")
    of_decennial_insurance = fields.Char(string="Decennial insurance")
    of_multirisk_insurance = fields.Char(string="Multi-risk insurance")
    of_qualif = fields.Char(string="Qualifications")
    of_general_id = fields.Char(string="General ID")
    of_accounting_id = fields.Char(string="Accountant ID")
    of_ref_mode = fields.Selection(selection=[
        ('no', "Do not fill"),
        ('id', "Use Partner ID"),
    ], string="Customer reference", required=True, default='no')

    def write(self, vals):
        if vals.get('of_ref_mode') == 'id':
            # On met à jour les contacts existants qui ont une référence vide
            partners = self.env['res.partner'].with_context(active_test=False).search(
                [('ref', '=', False), ('company_id', 'in', self._ids)])
            for partner in partners:
                if not self.env['res.partner'].with_context(active_test=False).search([('ref', '=', str(partner.id))]):
                    partner.ref = str(partner.id)
                else:
                    i = 2
                    while self.env['res.partner'].with_context(active_test=False).search([
                            ('ref', '=', f'{str(partner.id)}-{i}')]):
                        i += 1
                    partner.ref = f'{str(partner.id)}-{i}'
        return super().write(vals)

    @api.model
    def get_company_filter_ids(self):
        u"""
        Cette fonction renvois les informations nécessaires à l'utilisation du bouton de filtrage par société.
        Ce bouton est présent dans les vues calendrier et planning du module of_planning_view.
        Ainsi que le tableau de bord du module ks_dashboard_ninja.
        """
        companies = self.env.user.company_ids
        company_id = self.env.user.company_id.id
        filters = []
        for company in companies:
            fil = {'id': company.id, 'name': company.name}
            if company_id == company.id:
                fil['current'] = True
            filters.append(fil)
        return filters

    @api.model_create_multi
    def create(self, vals_list):
        if self._uid not in [SUPERUSER_ID, self.env.ref('base.user_admin').id]:
            raise ValidationError(_("Only the administrator can create a new company."))
        return super().create(vals_list)

    def unlink(self):
        if self._uid not in [SUPERUSER_ID, self.env.ref('base.user_admin').id]:
            raise ValidationError(_("Only the administrator can create a new company."))
        return super().unlink()
