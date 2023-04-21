# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFSector(models.Model):
    _name = 'of.sector'

    name = fields.Char(string="Title", required=True)
    code = fields.Char(string="Code")
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
    active = fields.Boolean(string="Active", default=True)
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

    # TODO: Remove me ? (not used)
    def get_internal_sectors(self, type='technical'):
        zip_range_obj = self.env['of.sector.zip.range']
        types = ('technical', 'technical_commercial') if type == 'tech' else ('commercial', 'technical_commercial')
        if len(self) == 1:
            zip_range_ids = self.env['of.sector.zip.range']
            for zip_range in self.zip_range_ids:
                under_zip_range_ids = zip_range_obj.search(
                    [('zip_code_min', '<=', zip_range.zip_code_max), ('zip_code_max', '>=', zip_range.zip_code_min)]
                )
                for under_zip_range_id in under_zip_range_ids:
                    if under_zip_range_id.sector_id.type in types:
                        zip_range_ids |= under_zip_range_id
            return zip_range_ids.mapped('sector_id').filtered(lambda s: s.id != self.id)
        elif len(self) > 1:
            res = {}
            for secteur in self:
                zip_range_ids = self.env['of.sector.zip.range']
                for zip_range in secteur.zip_range_ids:
                    under_zip_range_ids = zip_range_obj.search(
                        [('zip_code_min', '<=', zip_range.zip_code_max), ('zip_code_max', '>=', zip_range.zip_code_min)]
                    )
                    for under_zip_range_id in under_zip_range_ids:
                        if under_zip_range_id.sector_id.type in types:
                            zip_range_ids |= under_zip_range_id
                res[secteur.id] = zip_range_ids.mapped('sector_id').filtered(lambda s: s.id != secteur.id)
            return res

    @api.model
    def get_sector_from_zip_code(self, cp):
        return (
            self.env['of.sector.zip.range']
            .search(
                [('zip_code_min', '<=', cp), ('zip_code_max', '>=', cp)],
                order='zip_code_min DESC, zip_code_max',
                limit=1,
            )
            .sector_id
        )

    def get_partners(self):
        """Get partners of the sector.

        :return: Partners found
        :rtype: recordset of res.partner
        """
        partner_obj = self.env['res.partner']
        zip_range_obj = self.env['of.sector.zip.range']

        domain_partner = ['|'] * (len(self.mapped('zip_range_ids')) - 1)

        for zip_range in self.mapped('zip_range_ids'):
            zip_code_min = zip_range.zip_code_min
            zip_code_max = zip_range.zip_code_max
            inner_zip_ranges = zip_range_obj.search(
                [
                    ('zip_code_min', '>=', zip_code_min),
                    ('zip_code_min', '<=', zip_code_max),
                    ('id', '!=', zip_range.id),
                ],
                order='zip_code_min, zip_code_max DESC',
            )

            domain_sector = ['&'] * (len(inner_zip_ranges) + 1)
            domain_sector += [('zip', '>=', zip_code_min), ('zip', '<=', zip_code_max)]
            for inner_zip_range in inner_zip_ranges:
                if inner_zip_range.zip_code_max >= zip_code_min:
                    domain_sector += [
                        '|',
                        ('zip', '<', inner_zip_range.zip_code_min),
                        ('zip', '>', inner_zip_range.zip_code_max),
                    ]
                    zip_code_min = inner_zip_range.zip_code_max
            domain_partner += domain_sector

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
