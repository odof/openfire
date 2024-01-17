# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    of_request_id = fields.Many2one(
        comodel_name='of.service.request',
        string="Service Request",
        domain="of_address_id and ['|', ('address_id', '=', of_address_id), ('partner_id', '=', of_address_id)] or []",
    )
    of_type_id = fields.Many2one(
        comodel_name='of.service.request.type', string="Type", compute='_compute_of_type_id', store=True, readonly=False
    )

    @api.depends('of_state', 'of_template_id')
    def _compute_of_type_id(self):
        for event in self.filtered(lambda e: e.of_state == 'draft' and e.of_template_id and e.of_template_id.type_id):
            event.of_type_id = event.of_template_id.type_id

    @api.onchange('of_request_id')
    def _onchange_of_request_id(self):
        if not self.of_request_id:
            return

        self.of_task_id = self.of_request_id.task_id
        self.of_address_id = self.of_request_id.address_id or self.of_request_id.partner_id
        self.of_tag_ids = self.of_request_id.tag_ids
        if self.of_request_id.order_id:
            self.of_order_id = self.of_request_id.order_id
        if self.of_request_id.type_id:
            # When the intervention has a request associated to it, the type is readonly in the XML and is
            # therefore not written. The type assignment is merely cosmetic here
            self.of_type_id = self.of_request_id.type_id
        if self._context.get('of_import_request_lines'):
            self.of_fiscal_position_id = self.of_request_id.fiscal_position_id
            line_vals = [Command.clear()]
            line_vals.extend(
                Command.create(line._prepare_intervention_line_vals()) for line in self.of_request_id.line_ids
            )
            self.of_line_ids = line_vals
        if (  # self._origin contains the values of the DB record
            hasattr(self, '_origin')
            and self._origin.of_request_id.note
            and self._origin.of_request_id.note in (self._origin.of_internal_description or "")
        ):
            # If the description of the old request is still present, remove it.
            self.of_internal_description = self._origin.of_internal_description.replace(
                self._origin.of_request_id.note, ""
            )
        internal_description = self.of_internal_description or ""
        if self.of_request_id.note and self.of_request_id.note not in internal_description:
            # If the description of the new request is not already present, add it.
            self.of_internal_description = internal_description + self.of_request_id.note
