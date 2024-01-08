# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFSector(models.Model):
    _name = 'of.sector'

    name = fields.Char(string="Title", required=True)
    code = fields.Char()
    type = fields.Selection(
        selection=[
            ('technical', "Technical"),
            ('commercial', "Commercial"),
            ('technical_commercial', "Technical & Commercial"),
        ],
        string="Sector type",
        required=True,
        default='technical_commercial',
    )
    zip_range_ids = fields.One2many(comodel_name='of.sector.zip.range', inverse_name='sector_id', string="Postal codes")
    active = fields.Boolean(default=True)
    partner_count = fields.Integer(string="Number of partners", compute='_compute_partner_count')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Oops! Looks like this area already exists..."),
    ]

    def _compute_partner_count(self):
        for rec in self:
            rec.partner_count = len(
                self.env['res.partner'].search(
                    ['|', ('of_com_sector_id', '=', rec.id), ('of_tech_sector_id', '=', rec.id)]
                )
            )

    @api.model
    def get_sector_from_zip_code(self, cp, type_list=None):
        """Get sector from zip code."""
        domain = [('zip_code_min', '<=', cp), ('zip_code_max', '>=', cp)]
        if type_list:
            domain += [('sector_id.type', 'in', type_list)]
        return (
            self.env['of.sector.zip.range'].search(domain, order='zip_code_min DESC, zip_code_max', limit=1).sector_id
        )

    def get_partners(self):
        """Get partners of the sector.

        :return: Partners found
        :rtype: recordset of res.partner
        """
        partner_obj = self.env['res.partner']
        domain_partner = ['|'] * (len(self.mapped('zip_range_ids')) - 1)
        for zip_range in self.mapped('zip_range_ids'):
            domain_partner += ['&', ('zip', '>=', zip_range.zip_code_min), ('zip', '<=', zip_range.zip_code_max)]
        return partner_obj.search(domain_partner)

    def action_button_view_partner(self):
        self.ensure_one()
        action = self.env.ref('contacts.action_contacts')
        result = action.read()[0]
        del result['id']
        result['context'] = self._context.copy()
        partner_ids = (
            self.env['res.partner']
            .search(['|', ('of_com_sector_id', '=', self.id), ('of_tech_sector_id', '=', self.id)])
            .ids
            or []
        )
        result['domain'] = [('id', 'in', partner_ids)]
        return result

    def action_update(self, partners=None):
        self.ensure_one()
        if all_partners := partners or self.get_partners():
            if self.type in ('technical', 'technical_commercial'):
                all_partners.filtered(lambda p: not p.of_tech_sector_id).write({'of_tech_sector_id': self.id})
            if self.type in ('commercial', 'technical_commercial'):
                all_partners.filtered(lambda p: not p.of_com_sector_id).write({'of_com_sector_id': self.id})
        return True

    def action_update_delete(self):
        self.ensure_one()
        all_partners = self.get_partners()
        self.action_update(partners=all_partners)
        self.env['res.partner'].search([('id', 'not in', all_partners.ids), ('of_tech_sector_id', '=', self.id)]).write(
            {'of_tech_sector_id': False}
        )
        self.env['res.partner'].search([('id', 'not in', all_partners.ids), ('of_com_sector_id', '=', self.id)]).write(
            {'of_com_sector_id': False}
        )
        return True

    def action_button_update(self):
        for sector in self:
            sector.action_update()

    def action_button_update_delete(self):
        for sector in self:
            sector.action_update_delete()

    def action_button_toggle_active(self):
        for sector in self:
            sector.active = not sector.active
