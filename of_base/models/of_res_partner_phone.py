# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, api, fields
from .res_partner import PHONE_TYPES
from .res_partner import convert_phone_number


class OFResPartnerPhone(models.Model):
    _name = 'of.res.partner.phone'
    _inherit = ['mail.thread']
    _order = 'type, id'
    _rec_name = 'number'

    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner", index=True, ondelete='cascade')
    number = fields.Char(string="Number")
    number_display = fields.Char(
        string="Number in national format", compute='_compute_number_display', inverse='_inverse_number_display',
        tracking=True)
    type = fields.Selection(selection=PHONE_TYPES, string="Number type", required=True)
    title_id = fields.Many2one(
        comodel_name="res.partner.title", string="Civility of the number", domain="[('of_used_for_phone', '=', True)]")
    is_valid = fields.Boolean(string="Is a valid number ?", compute='_compute_is_valid', store=True)

    @api.depends('number')
    def _compute_number_display(self):
        user_country_code = self.env.user.country_id.code or self.env.user.company_id.country_id.code or 'FR'
        for rec in self:
            if rec.is_valid:
                rec.number_display = convert_phone_number(rec.number, user_country_code, new_format='country')
            else:
                rec.number_display = rec.number

    def _inverse_number_display(self):
        default_country_code = self.env.user.country_id.code or self.env.user.company_id.country_id.code or 'FR'
        for rec in self:
            number = convert_phone_number(rec.number_display, default_country_code, strict=True)
            if not number:
                country_code = rec.partner_id.country_id and rec.partner_id.country_id.code or default_country_code
                number = convert_phone_number(rec.number_display, country_code)
            rec.number = number

    @api.depends('number')
    def _compute_is_valid(self):
        for rec in self:
            rec.is_valid = bool(convert_phone_number(rec.number, strict=True))

    @api.onchange('number_display')
    def _onchange_number_display(self):
        default_country_code = self.env.user.country_id.code or self.env.user.company_id.country_id.code or 'FR'
        for rec in self:
            number = convert_phone_number(rec.number_display, default_country_code, strict=True)
            if not number:
                country_code = rec.partner_id.country_id and rec.partner_id.country_id.code or default_country_code
                number = convert_phone_number(rec.number_display, country_code)
            rec.number = number

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number', False):
                partner_id = vals.get('partner_id', False)
                if partner_id:
                    partner = self.env['res.partner'].browse(partner_id)
                    country_code = (partner.country_id and partner.country_id.code) or \
                        (self.env.user.company_id.country_id and self.env.user.company_id.country_id.code) or \
                        "FR"
                vals['number'] = convert_phone_number(vals.get('number'), country_code)
        return super(OFResPartnerPhone, self.with_context(mail_create_nolog=True)).create(vals_list)

    def write(self, vals):
        if vals.get('number', False):
            partner = self[0].partner_id
            country_code = (partner.country_id and partner.country_id.code) or \
                (self.env.user.company_id.country_id and self.env.user.company_id.country_id.code) or \
                "FR"
            vals['number'] = convert_phone_number(vals.get('number'), country_code)
        return super().write(vals)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if args and len(args) == 1 and args[0][0] == 'number' and args[0][2] and args[0][2][0] == '0':
            args = [(args[0][0], args[0][1], args[0][2][1:].replace(" ", ""))]
        return super()._search(
            args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    def message_post(self, body='', subject=None, message_type='notification',
                     subtype=None, parent_id=False, attachments=None,
                     content_subtype='html', **kwargs):
        self.ensure_one()
        if self.partner_id:
            self.partner_id.message_post(body=body, subject=subject, message_type=message_type,
                                         subtype=subtype, parent_id=parent_id, attachments=attachments,
                                         content_subtype=content_subtype, **kwargs)
        return super().message_post(
            body=body, subject=subject, message_type=message_type, subtype=subtype, parent_id=parent_id,
            attachments=attachments, content_subtype=content_subtype, **kwargs)
