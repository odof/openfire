# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    of_task_ids = fields.Many2many(
        comodel_name='of.planning.task',
        relation='of_employee_task_rel',
        column1='employee_id',
        column2='task_id',
        string="Tasks",
        help="Defines the tasks for which the employee is qualified.\n"
        "Tasks can be set in the \"Tasks\" submenu of the intervention configuration.",
    )
    of_all_tasks = fields.Boolean(
        string="Able to handle all task",
        default=True,
    )
    of_team_ids = fields.Many2many(
        comodel_name='of.planning.team',
        relation='of_team_employee_rel',
        column1='employee_id',
        column2='team_id',
        string="Teams",
        help="Allows you to assign one or more teams to the employee.",
    )
    of_is_operator = fields.Boolean(
        string="Is an operator", default=False, help="Defines whether the employee is a technician."
    )
    of_is_salesperson = fields.Boolean(
        string="Is a salesperson", default=False, help="Defines whether the employee is a salesperson."
    )
    of_daily_email = fields.Boolean(
        string="Send email a day before the appointment",
        default=False,
        help="Allows you to send the employee's schedule each evening by email when the employee has work "
        "to do the next day.",
    )

    def is_able(self, task, all_required=False):
        """
        Returns True if employees in self can perform the task. Unless all_required=True, it is sufficient for
        one of the employee to perform the task for the function to return True.
        :param task: The task
        :param all_required: True if all employees must know how to perform the task
        :return: True if is able, else False
        :rtype Boolean
        """
        if all_required:
            return all((task.id in e.of_task_ids.ids or e.of_all_tasks) for e in self)
        return any((task.id in e.of_task_ids.ids or e.of_all_tasks) for e in self)

    @api.model
    def cron_planning_send_tomorrow_schedule_by_mail(self):
        """
        This method is used to automatically send planning emails to employees who have the 'of_daily_email' field
        set to True.
        It generates a planning report for each employee, attaches it to an email, and sends it using a predefined
        email template.
        """
        _logger.info('# Cron job: Send planning emails to employees')
        timezone = self._context.get('tz') or self.env.user.partner_id.tz or 'UTC'

        # convert date and time into user timezone
        self_tz = self.with_context(tz=timezone)

        start_date = fields.Datetime.context_timestamp(self_tz, fields.Datetime.now()) + relativedelta(days=1)
        start_date = start_date.replace(hour=5, minute=0, second=0)

        # Group employees by company
        employees_by_company = {}
        for employee in self.search([('of_daily_email', '=', True)]):
            company = employee.company_id
            if company not in employees_by_company:
                employees_by_company[company] = []
            employees_by_company[company].append(employee)

        # Send emails by company
        for company, employees in employees_by_company.items():
            _logger.info(
                '> Sending planning (%s) emails to employees of company %s',
                start_date.strftime('%Y-%m-%d'),
                company.name,
            )
            wz_report = self.env['of.planning.print.wizard'].create(
                {
                    'report_type': 'day',
                    'start_date': start_date,
                }
            )
            for employee in employees:
                _logger.info('  > Generating planning for employee %s', employee.name)
                if not wz_report._get_employee_interventions(employee.id):
                    _logger.info('    > No interventions found for employee %s', employee.name)
                    continue

                wz_report.employee_ids = [Command.set([employee.id])]
                generated_report, report_extension = self.env['ir.actions.report']._render_qweb_pdf(
                    'of_planning.report_planning_day', res_ids=[wz_report.id]
                )

                report_attachment = (
                    self.env['ir.attachment']
                    .sudo()
                    .create(
                        {
                            'name': f"Planning_{start_date.strftime('%Y%m%d')}.{report_extension}",
                            'type': 'binary',
                            'datas': base64.b64encode(generated_report),
                            'mimetype': 'application/pdf',
                            'res_model': 'hr.employee',
                            'res_id': employee.id,
                        }
                    )
                )
                email_template = self.env.ref('of_planning.email_template_planning')
                email_values = {
                    'email_to': employee.work_contact_id.email_formatted,
                    'email_from': company.email_formatted,
                }
                email_template.attachment_ids = [Command.set([report_attachment.id])]
                email_template.send_mail(employee.id, email_values=email_values, force_send=True)
                _logger.info('    > Planning email sent to employee %s', employee.name)
        _logger.info('# Cron job: Send planning emails to employees finished')
