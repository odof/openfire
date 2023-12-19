# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFPlanningTask(models.Model):
    _name = 'of.planning.task'
    _description = "Task"
    _order = 'sequence'

    name = fields.Char(size=100, required=True)
    description = fields.Text()
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=1, help="Used to order tasks. Lower is better.")
    display = fields.Selection(
        selection=[
            ('hide', "Don't display"),
            ('internal_description', "In the internal description"),
            ('external_description', "In the external description"),
        ],
        string="Display description",
        default='internal_description',
    )
    is_locked = fields.Boolean(string="Locked")
    product_id = fields.Many2one(comodel_name='product.product', string="Product")
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string="Fiscal position", company_dependent=True
    )
    duration = fields.Float(string="Default duration", default=1.0)
    team_ids = fields.Many2many(
        comodel_name='of.planning.team',
        relation='of_team_task_rel',
        column1='task_id',
        column2='team_id',
        string="Qualified teams",
    )
    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        string="Qualified employees",
        compute='_compute_employee_ids',
        search='_search_employee_ids',
    )
    planning_granularity = fields.Selection(
        selection=[
            ('weekly', "Weekly"),
            ('fortnightly', "Fortnightly"),
            ('monthly', "Monthly"),
        ],
        string="Planning granularity",
        help="Granularity is used to define the reference planning period by task type. "
        "This granularity is used to calculate the end date once the start date has been entered, "
        "to calculate the end date once the start date has been entered.\nDefault:\n"
        "  * For an installation, the planning granularity is fortnightly.\n"
        "  * For an after-sales service (when the after-sales service field is filled in), the planning granularity is "
        "weekly.\n"
        "  * For maintenance (recurring operations), the planning granularity is monthly.",
    )
    templates_ids = fields.Many2many(
        comodel_name='of.planning.intervention.template',
        compute='_compute_templates_ids',
        string="Templates",
        copy=False,
        store=True,
    )
    templates_count = fields.Integer(string="# Templates", compute='_compute_templates_ids')

    def _compute_templates_ids(self):
        intervention_template_obj = self.env['of.planning.intervention.template']
        for task in self:
            templates = intervention_template_obj.search([('task_id', '=', task.id)])
            task.templates_ids = templates
            task.templates_count = len(templates)

    def _compute_employee_ids(self):
        employees = self.env['hr.employee'].search(
            ['|', ('of_is_operator', '=', True), ('of_is_salesperson', '=', True)]
        )
        for task in self:
            task.employee_ids = employees.filtered(lambda i: i.of_all_tasks or task.id in i.of_all_tasks.ids)

    def _search_employee_ids(self, operator, value):
        """/!\\ Only 'in' et 'not in' case are treated"""
        tasks = self.search([])

        if operator == 'in':
            tasks = tasks.filtered(lambda t: set(t.employee_ids.ids).intersection(value))
        elif operator == 'not in':
            tasks = tasks.filtered(lambda t: not set(t.employee_ids.ids).intersection(value))

        return [('id', 'in', tasks.ids)]

    def action_button_view_template(self):
        return self._get_action_view_template(self.templates_ids)

    def _get_action_view_template(self, templates):
        self.ensure_one()
        result = self.env["ir.actions.actions"]._for_xml_id('of_planning.action_of_planning_intervention_template')
        # choose the view_mode accordingly
        if not templates or len(templates) > 1:
            result['domain'] = [('id', 'in', templates.ids)]
        elif len(templates) == 1:
            res = self.env.ref('of_planning.of_planning_intervention_template_view_form', False)
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view + [(state, view) for state, view in result.get('views', []) if view != 'form']
            result['res_id'] = templates.id
        return result
