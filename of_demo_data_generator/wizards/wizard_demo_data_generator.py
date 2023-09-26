# -*- coding: utf-8 -*-

import datetime
import random

from odoo import _, api, fields, models

from odoo.addons.of_utils.models.of_utils import float_2_heures_minutes


class WizardDemoDataGenerator(models.TransientModel):
    _name = 'wizard.generate.demo.data'

    # Company data
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    zip = fields.Char(string='Zip')

    # Employee data
    employee_ids = fields.Many2many(
        comodel_name='hr.employee', string='Employees', required=True)

    # Customer data
    contact_type = fields.Selection(
        string='Contact type', selection=[('customer', 'Customer'), ('prospect', 'Prospect')]
    )

    # Number of records to generate
    number_of_interventions = fields.Integer(string='Number of interventions', default=10)

    # Intervention data
    template_id = fields.Many2one(
        comodel_name='of.planning.intervention.template', string='Template')
    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.street = self.company_id.street
        self.street2 = self.company_id.street2
        self.city = self.company_id.city
        self.zip = self.company_id.zip

    def _get_partners(self):
        return self.env['res.partner'].search(
            [
                ('is_company', '=', True),
                ('customer', '=', True),
                ('company_id', '=', self.company_id.id),
            ]
        )

    def _get_intervention_templates(self):
        return self.env['of.planning.intervention.template'].search([])

    def _get_tasks_from_employee(self, employee):
        return employee.mapped('of_tache_ids').filtered(lambda t: t.duree < 5.0)

    @api.multi
    def generate_interventions(self):
        intervention_obj = self.env['of.planning.intervention']

        partners = self._get_partners()
        templates = self._get_intervention_templates()

        date_from = datetime.datetime.strptime(self.date_from, '%Y-%m-%d')
        date_to = datetime.datetime.strptime(self.date_to, '%Y-%m-%d')
        hours_list = [8, 9, 10, 11, 13, 14, 15, 16]
        minutes_list = [0, 15, 30, 45]

        created_interventions = intervention_obj.browse([])

        for _ in range(self.number_of_interventions):
            # Get a random partner
            partner = partners[random.randint(0, len(partners) - 1)]

            if not self.template_id:
                # Get a random template
                template = templates[random.randint(0, len(templates) - 1)]
            else:
                template = self.template_id

            # Get a random employee
            employee = self.employee_ids[random.randint(0, len(self.employee_ids) - 1)]

            # Get the tasks from the employee
            tasks = self._get_tasks_from_employee(employee)

            # Get a random date
            date = date_from + datetime.timedelta(days=random.randint(0, (date_to - date_from).days))
            random_hour = hours_list[random.randint(0, len(hours_list) - 1)]
            random_minute = minutes_list[random.randint(0, len(minutes_list) - 1)]
            date = date.replace(hour=random_hour, minute=random_minute, second=0, microsecond=0)

            # Create the intervention
            intervention = self.env['of.planning.intervention'].new(
                {
                    'employee_ids': [(4, employee.id)],
                    'date': date,
                    'partner_id': partner.id,
                    'template_id': template.id,
                    'company_id': self.company_id.id,
                    'forcer_dates': True,
                    'verif_dispo': False,
                }
            )
            intervention.onchange_template_id()
            intervention._onchange_partner_id()
            intervention._onchange_address_id()
            intervention.onchange_company_id()
            if not intervention.tache_id:
                random_task = tasks[random.randint(0, len(tasks) - 1)]
                intervention.tache_id = random_task.id
                intervention._onchange_tache_id()
            intervention._compute_date_deadline()
            intervention_vals = intervention._convert_to_write(intervention._cache)
            heures, minutes = float_2_heures_minutes(intervention.duree)
            intervention_vals['date_deadline_forcee'] = date + datetime.timedelta(hours=heures, minutes=minutes)
            created_interventions |= intervention_obj.create(intervention_vals)
        return created_interventions

    @api.multi
    def action_button_generate_demo_data(self):
        interventions = self.generate_interventions()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Interventions'),
            'res_model': 'of.planning.intervention',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', interventions.ids)],
        }
