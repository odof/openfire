# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFServiceRequestEquipmentLine(models.Model):
    """Class to link service request equipment to an Intervention (`calendar.event`).
    That allow user to see quickly from the Service Request for which equipment an intervention is planned/done.
    """

    _name = 'of.service.request.equipment.line'
    _order = 'request_id, start asc, event_id, equipment_id'
    _description = "See for which equipment of a Service Request an intervention is planned/done."

    request_id = fields.Many2one(
        comodel_name='of.service.request',
        string="Service Request",
        required=True,
        ondelete='cascade',
    )
    event_id = fields.Many2one(
        comodel_name='calendar.event',
        string="Event",
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string="Name", related='event_id.name')
    start = fields.Datetime(string="Date", related='event_id.start', store=True)
    state = fields.Selection(string="State", related='event_id.of_state')
    operator_id = fields.Many2one(string="Operator", related='equipment_id.operator_id')
    equipment_id = fields.Many2one(
        comodel_name='of.equipment',
        string="Equipment",
        required=True,
    )
