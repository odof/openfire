# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class OFGeoWizard(models.TransientModel):
    _name = 'of.geo.wizard'
    _description = "Geocoding of selected partners"

    @api.model
    def _get_partner_ids(self):
        if model := self._context.get('active_model'):
            obj = self.env[model].browse(self._context.get('active_ids', []))
            if model == 'res.partner':
                partners = obj
            elif model == 'res.company':
                partners = obj.mapped('partner_id')
            else:
                raise UserError(_("Unable to launch this wizard from the object %s") % model)
        else:  # en cas de rafraichissement page: choisir les partenaires du dernier wizard
            wizard = self.env['of.geo.wizard'].browse()
            partners = wizard and wizard[-1].partner_ids or self.env['res.partner']

        return partners

    update_all_selected = fields.Boolean(string="Update all selected")
    update_all_selected_except_manual_geolocalized = fields.Boolean(
        string="Update all selected except manual geolocalized contacts"
    )
    update_also_failed = fields.Boolean(string="Update also in case of failure")
    partner_ids = fields.Many2many(comodel_name='res.partner', string="Selected Partners", default=_get_partner_ids)
    # geolocalization results
    line_ids = fields.One2many(
        comodel_name='of.geo.wizard.line', inverse_name='wizard_id', string="Partners to geolocalize"
    )
    is_geolocalize_done = fields.Boolean(string="Geolocalize done", default=False)

    # statistics
    number_selected_partners = fields.Integer(
        string="Number of Selected Partners", compute='_compute_partners_according_to_state', readonly=True
    )
    number_selected_partners_success = fields.Integer(
        string="Number of Geolocalized Partners", compute='_compute_partners_according_to_state', readonly=True
    )
    number_selected_partners_manual = fields.Integer(
        string="Number of Manual Geolocalized Partners", compute='_compute_partners_according_to_state', readonly=True
    )
    number_selected_partners_failure = fields.Integer(
        string="Number of Failed Geolocalized Partners", compute='_compute_partners_according_to_state', readonly=True
    )
    number_selected_partners_without_address = fields.Integer(
        string="Number of Partners without address", compute='_compute_partners_according_to_state', readonly=True
    )
    number_selected_partners_not_tried = fields.Integer(
        string="Number of Partners not geolocalized yet", compute='_compute_partners_according_to_state', readonly=True
    )
    number_selected_partners_to_geolocalize = fields.Integer(
        string="Number Partners to geolocalize", compute='_compute_partners_according_to_state', readonly=True
    )

    @api.model
    def _geo_localize(self, street='', zip='', city='', state='', country=''):
        geo_obj = self.env['base.geocoder']
        search = geo_obj.geo_query_address(street=street, zip=zip, city=city, state=state, country=country)
        result = geo_obj.geo_find(search, force_country=country)
        if result is None:
            search = geo_obj.geo_query_address(city=city, state=state, country=country)
            result = geo_obj.geo_find(search, force_country=country)
        return result

    def _prepare_line_vals(self, partner, result, precision):
        """Prepare the values to create a line in the wizard, according to the geolocalization result"""
        return {
            'partner_id': partner.id,
            'partner_latitude': result[0],
            'partner_longitude': result[1],
            'date_localization': fields.Date.context_today(partner),
            'response_json': json.dumps(result[2][0], indent=3, sort_keys=True, ensure_ascii=False),
            'geocoding_state': 'success',
            'requested_address': partner.get_addr_params(),
            'response_address': result[2][0]['display_name'],
            'precision': precision,
        }

    def _prepare_line_vals_empty(self, partner):
        """Prepare the values to create a line in the wizard, when the partner has no address"""
        return {
            'partner_id': partner.id,
            'partner_latitude': 0.0,
            'partner_longitude': 0.0,
            'response_json': '',
            'geocoding_state': 'no_address',
        }

    def _get_partners_to_update(self):
        """Get the partners to update according to the wizard options"""
        if self.update_all_selected_except_manual_geolocalized:
            return self.partner_ids.filtered(lambda p: p.of_geocoding_state not in ['no_address', 'manual'])

        elif self.update_all_selected:
            return self.partner_ids.filtered(lambda p: p.of_geocoding_state != 'no_address')

        else:
            return self.partner_ids.filtered(lambda p: p.of_geocoding_state not in ['no_address', 'success'])

    def _geo_localize_and_add_line(self, partner):
        """Geolocalize the partner and add a line in the wizard if successfully geolocalized"""
        if result := self._geo_localize(
            partner.street, partner.zip, partner.city, partner.state_id.name, partner.country_id.name
        ):
            rank = result[2][0]['place_rank']
            precision = partner._determine_precision(rank)
            vals = self._prepare_line_vals(partner, result, precision)
            self.line_ids = [Command.create(vals)]

    def action_button_geolocalize(self):
        """Button action to geolocalize the selected partners"""
        to_update = self._get_partners_to_update()
        if len(to_update) > 0:
            for partner in to_update.with_context(lang='en_US'):
                if partner.street or partner.zip or partner.city or partner.state_id or partner.country_id:
                    self._geo_localize_and_add_line(partner)
                else:
                    vals = self._prepare_line_vals_empty(partner)
                    self.line_ids = [Command.create(vals)]
            self.is_geolocalize_done = True

    def action_button_validate(self):
        """Button action to validate the geolocalization results and update the partners"""
        date_last_localization = fields.Datetime.context_timestamp(self, fields.datetime.now())
        if not self.line_ids:
            raise UserError(_("You must select a result before you can validate"))
        if self.update_also_failed:
            self.line_ids = self.line_ids
        else:
            self.line_ids.filtered(lambda p: p.geocoding_state != 'failure')
        for line in self.line_ids:
            vals = {
                'id': line.partner_id,
                'partner_latitude': line.partner_latitude,
                'partner_longitude': line.partner_longitude,
                'date_localization': date_last_localization,
                'of_response_json': line.response_json,
                'of_geocoding_state': line.geocoding_state,
                'of_precision': line.precision,
            }
            if line.geocoding_state != 'success':
                vals['partner_latitude'] = 0
                vals['partner_longitude'] = 0
                vals['of_geocoding_state'] = 'no_address'
                vals['of_response_json'] = ""
                vals['of_precision'] = 'unknown'
            line.partner_id.write(vals)

        url = f"/web#action={self.env.ref('contacts.action_contacts').id}&model=res.partner&view_type=list"
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': url,
        }

    def action_button_cancel(self):
        url = f"/web#action={self.env.ref('contacts.action_contacts').id}&model=res.partner&view_type=list"
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': url,
        }

    @api.onchange('partner_ids', 'update_all_selected', 'update_all_selected_except_manual_geolocalized')
    def _compute_partners_according_to_state(self):
        partners = self.partner_ids
        self.number_selected_partners = len(partners)
        self.number_selected_partners_success = len(partners.filtered(lambda p: p.of_geocoding_state == 'success'))
        self.number_selected_partners_manual = len(partners.filtered(lambda p: p.of_geocoding_state == 'manual'))
        self.number_selected_partners_failure = len(partners.filtered(lambda p: p.of_geocoding_state == 'failure'))
        self.number_selected_partners_without_address = len(
            partners.filtered(lambda p: p.of_geocoding_state == 'no_address')
        )
        self.number_selected_partners_not_tried = len(partners.filtered(lambda p: p.of_geocoding_state == 'not_tried'))
        if self.update_all_selected:
            self.number_selected_partners_to_geolocalize = (
                self.number_selected_partners - self.number_selected_partners_without_address
            )
        elif self.update_all_selected_except_manual_geolocalized:
            self.number_selected_partners_to_geolocalize = (
                self.number_selected_partners
                - self.number_selected_partners_without_address
                - self.number_selected_partners_manual
            )
        else:
            self.number_selected_partners_to_geolocalize = (
                self.number_selected_partners
                - self.number_selected_partners_without_address
                - self.number_selected_partners_success
            )
