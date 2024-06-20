# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    of_use_equipment = fields.Boolean(
        string="Use Equipment", help="Activate this field to add one or more items of equipment to be worked on."
    )
    of_equipment_ids = fields.Many2many(
        comodel_name='of.equipment',
        relation='of_calendar_event_equipment_rel',
        column1='intervention_id',
        column2='equipment_id',
        string="Equipments",
        domain="['|', '|', ('customer_id', '=', of_partner_id), "
        "('customer_id', '=', of_address_id), ('site_address_id', '=', of_address_id)]",
        compute='_compute_of_equipment_ids',
        store=True,
        readonly=False,
    )
    of_history_equipment_ids = fields.One2many(
        comodel_name='calendar.event',
        compute='_compute_of_history_equipment_ids',
        string="History (Equipment)",
    )

    @api.constrains('of_equipment_ids', 'of_use_equipment')
    def _check_of_equipment_ids(self):
        if self._context.get('ignore_equipment_ids_check'):
            return
        for event in self:
            if event.of_use_equipment:
                if len(event.of_equipment_ids) > 1:
                    raise ValidationError(_("Please add only one equipment."))
                elif len(event.of_equipment_ids) == 0:
                    raise ValidationError(_("Please add at least one equipment."))

    @api.depends('of_equipment_ids')
    def _compute_of_history_intervention_ids(self):
        super()._compute_of_history_intervention_ids()
        for event in self:
            interventions = self.env['calendar.event'].browse()
            if event.of_address_id:
                interventions = event.of_address_id.of_intervention_address_ids
            elif event.of_partner_id:
                interventions = event.of_partner_id.of_intervention_partner_ids

            event.of_history_intervention_ids = (
                self.search(
                    [
                        ('id', 'in', interventions.ids),
                        ('start', '<', event.start),
                        '|',
                        ('of_equipment_ids', '=', False),
                        ('of_equipment_ids', 'not in', event.of_equipment_ids.ids),
                    ]
                )
                if interventions
                else False
            )

    @api.depends('of_use_equipment', 'of_address_id', 'of_partner_id')
    def _compute_of_equipment_ids(self):
        equipment_obj = self.env['of.equipment']
        events_use_equipment = self.filtered('of_use_equipment')
        for event in events_use_equipment:
            equipments = equipment_obj.search(
                [('site_address_id', '=', event.of_address_id.id)]
            ) or equipment_obj.search([('customer_id', '=', event.of_address_id.id)])
            if not equipments and event.of_partner_id:
                equipments = equipment_obj.search([('customer_id', '=', event.of_partner_id.id)])
            if len(equipments) == 1:
                event.of_equipment_ids = equipments
            else:
                event.of_equipment_ids = False
        for event in self - events_use_equipment:
            event.of_equipment_ids = False

    @api.depends('of_equipment_ids')
    def _compute_of_history_equipment_ids(self):
        events_with_equipment = self.filtered(lambda e: e.of_equipment_ids)
        for event in events_with_equipment:
            event.of_history_equipment_ids = event.mapped('of_equipment_ids.intervention_ids').filtered(
                lambda i: event.start > i.start
            )
        for event in self - events_with_equipment:
            event.of_history_equipment_ids = self.env['calendar.event'].browse()

    def action_button_open_intervention(self):
        self.ensure_one()
        view_id = self.env.ref('of_planning.calendar_event_view_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': "Interventions",
            'res_model': 'calendar.event',
            'res_id': self.ids[0],
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'target': 'current',
        }
