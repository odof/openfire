# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

OF_CRM_STAGE_IDS = [
    ('1', "1"),
    ('2', "2"),
    ('3', "3"),
    ('4', "4"),
    ('5', "5"),
    ('6', "6"),
    ('7', "7"),
    ('8', "8"),
    ('9', "9"),
    ('10', "10"),
    ('11', "11"),
    ('12', "12"),
    ('13', "13"),
    ('14', "14"),
    ('15', "15"),
    ('16', "16"),
    ('17', "17"),
    ('18', "18"),
    ('19', "19"),
    ('20', "20")
]


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    of_crm_stage_id = fields.Selection(
        selection=OF_CRM_STAGE_IDS, string="Source Opportunity Stage ID", copy=False)

    _sql_constraints = [
        ('of_crm_stage_id_uniq', 'unique (of_crm_stage_id)', "There is already a kanban step with this identifier")
    ]
