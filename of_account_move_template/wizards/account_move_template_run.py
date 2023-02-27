# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import calendar
from datetime import date as dt_date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError


class WizardSelectMoveTemplate(models.TransientModel):
    _inherit = 'account.move.template.run'

    of_template_ids = fields.Many2many(
        comodel_name='account.move.template', relation='account_move_template_run_template_rel', column1='wizard_id',
        column2='template_id', string="Templates")
    of_recurring = fields.Boolean(string="Recurring")
    of_rec_interval = fields.Integer(string="Repeat every", default=1, required=True)
    of_rec_interval_type = fields.Selection(
        selection=[('days', "Days"), ('months', "Months"), ('years', "Years")],
        string="Time unit", default='months', required=True)
    of_rec_number = fields.Integer(string="Number of vouchers", default=12, required=True)
    of_date_start = fields.Date(string="Start date", default=fields.Date.today, required=True)
    of_prorata = fields.Boolean(
        string="Prorata",
        help="The amount of the entries will be adjusted pro rata to the month on the first and last month.")
    of_reversal = fields.Selection(selection=[
        ('none', "No reversal"), ('first', "Start date"), ('last', "End date"), ('custom', "Chosen date")],
        string="Reverse the entry", default='none', required=True)
    of_reversal_date = fields.Date(string="Reversal date")

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if (
            'of_template_ids' in fields_list
            and 'template_id' in fields_list
            and self._context.get('active_model') == 'account.move.template'
        ):
            template_ids = self._context['active_ids'] or []
            if len(template_ids) > 1:
                # La génération depuis des modèles multiples n'est autorisée que si ils sont entièrement calculés
                templates = self.env['account.move.template'].browse(template_ids).filtered(
                    lambda t: t.line_ids.filtered(lambda line: line.type == 'input'))
                if templates:
                    raise UserError(_(
                        "Generating from several models simultaneously requires that they do not have amounts "
                        "in manual entry.\nModel(s) in error: %s") % ', '.join(templates.mapped('name')))
            result['of_template_ids'] = template_ids
            result['template_id'] = template_ids and template_ids[0] or False
        return result

    def load_lines(self):
        """ Override the function to not automatically generate accounting pieces when there is no line with
        "manual" amount and the model indicates a recurrence.
        """
        self.ensure_one()
        # Verify and get overwrite dict
        overwrite_vals = self._get_overwrite_vals()
        amtlro = self.env["account.move.template.line.run"]
        if self.company_id != self.template_id.company_id:
            raise UserError(
                _(
                    "The selected template (%(template)s) is not in the same company "
                    "(%(company)s) as the current user (%(user_company)s).",
                    template=self.template_id.name,
                    company=self.template_id.company_id.display_name,
                    user_company=self.company_id.display_name,
                )
            )
        tmpl_lines = self.template_id.line_ids
        for tmpl_line in tmpl_lines.filtered(lambda line: line.type == 'input'):
            vals = self._prepare_wizard_line(tmpl_line)
            amtlro.create(vals)

        # Values to write on the wizard
        values = {
            'journal_id': self.template_id.journal_id.id,
            'ref': self.template_id.ref,
            'state': 'set_lines',
        }
        # Update values with openfire specific values
        data = self.template_id.read([
            'of_recurring', 'of_rec_interval', 'of_rec_interval_type', 'of_rec_number', 'of_prorata',
            'of_reversal', 'of_reversal_date'])[0]
        if data['of_reversal_date']:
            reversal_date = fields.Date.from_string(data['of_reversal_date'])
            month_start = dt_date.today() + relativedelta(day=1)
            reversal_date += relativedelta(year=month_start.year)
            if reversal_date < month_start:
                reversal_date += relativedelta(years=1)
            data['of_reversal_date'] = reversal_date
        values.update(data)
        # Write all values
        self.write(values)

        if not self.line_ids and not self.template_id.of_recurring:
            return self.generate_move()

        action = self.env.ref('account_move_template.account_move_template_run_action')
        result = action.sudo().read()[0]
        result.update({'res_id': self.id, 'context': self.env.context})

        # Overwrite self.line_ids to show overwrite values
        self._overwrite_line(overwrite_vals)
        # Pass context furtner to generate_move function, only readonly field
        for key in overwrite_vals.keys():
            overwrite_vals[key].pop("amount", None)
        context = result.get("context", {}).copy()
        context.update({"overwrite": overwrite_vals})
        result['context'] = context
        return result

    def get_relative_delta(self, recurring_rule_type, interval, day=None):
        if recurring_rule_type == 'days':
            return relativedelta(days=interval)
        elif recurring_rule_type == 'months':
            return relativedelta(months=interval, day=day)
        elif recurring_rule_type == 'years':
            return relativedelta(years=interval)
        else:
            raise UserError(_("Wrong value for recurring rule type."))

    def generate_move(self, sequence2amount, params, template):
        self.ensure_one()
        move_obj = self.env['account.move']
        name = template.name
        journal_id = template.journal_id
        company_cur = self.company_id.currency_id
        amounts = template.compute_lines(sequence2amount)
        totals = {sequence: 0 for sequence in amounts}
        moves = move_obj.browse()  # empty recordset
        date_start = self.of_date_start
        month_last_day = calendar.monthrange(date_start.year, date_start.month)[1]
        of_prorata = self.of_rec_interval_type == 'months' and self.of_prorata

        if all(company_cur.is_zero(x) for x in amounts.values()):
            raise UserError(_("Debit and credit of all lines are null."))

        # Calcul des dates des pièces comptables.
        dates = [date_start]
        if params.of_recurring:
            self._fill_move_dates_list(params, date_start, month_last_day, dates)

        # Génération des pièces comptables.
        imax = len(dates) - 1
        for i, date in enumerate(dates):
            date_amounts = amounts
            if i == 0 and of_prorata:
                if params.of_recurring:
                    ratio = float(month_last_day - date_start.day + 1) / month_last_day
                    date_amounts = {sequence: amount * ratio for sequence, amount in date_amounts.items()}
                    amt0 = date_amounts
            elif i == imax and of_prorata:
                if params.of_recurring:
                    date_amounts = {
                        sequence: amount - amt0[sequence]
                        for sequence, amount in date_amounts.items()
                    }

            for sequence, amount in date_amounts.items():
                totals[sequence] += amount

            move_vals = self._prepare_move(name=name, template_id=template.id, date=date, journal_id=journal_id.id)
            for line in template.line_ids:
                amount = date_amounts[line.sequence]
                if not company_cur.is_zero(amount):
                    move_vals['line_ids'].append(
                        Command.create(self._prepare_move_line(line, amount))
                    )
            moves |= move_obj.create(move_vals)

        if params.of_recurring and params.of_reversal != 'none':
            if params.of_reversal == 'first':
                date = self.of_date_start
            elif params.of_reversal == 'last':
                date = moves[-1].date
            else:
                # Date custom
                date = params.of_reversal_date

            move_vals = self._prepare_move(name=name, template_id=template.id, date=date, journal_id=journal_id.id)
            for line in template.line_ids:
                amount = totals[line.sequence]
                if not company_cur.is_zero(amount):
                    line_values = self._prepare_move_line(line, amount)
                    line_values['credit'], line_values['debit'] = line_values['debit'], line_values['credit']
                    move_vals['line_ids'].append(
                        Command.create(line_values)
                    )
            moves |= move_obj.create(move_vals)
        return moves

    def generate_moves(self):
        self.ensure_one()
        moves = self.env['account.move'].browse()
        name = ""
        if len(self.of_template_ids) > 1:
            for template in self.of_template_ids:
                sequence2amount = {}
                moves |= self.generate_move(sequence2amount, template, template)
        else:
            sequence2amount = {
                template_line.sequence: template_line.amount
                for template_line in self.line_ids
            }
            name = f" : {self.template_id.name}"
            moves |= self.generate_move(sequence2amount, self, self.template_id)

        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_line_form')
        action['name'] = _("Entries generated from template%s") % name
        action['domain'] = [('id', 'in', moves.ids)]
        return action

    def _prepare_move(self, name=False, template_id=False, date=False, journal_id=False):
        """ Prepare the values to create the move from the template.

        :param name: The name of the move.
        :param template_id: The id of the template.
        :param date: The date of the move.
        :param journal_id: The id of the journal.
        :return: A dictionary of values to create the move.
        """
        move_vals = super()._prepare_move()
        if name:
            move_vals['name'] = name
        if template_id:
            move_vals['of_template_id'] = template_id
        if date:
            move_vals['date'] = date
        if journal_id:
            move_vals['journal_id'] = journal_id
        return move_vals

    def _fill_move_dates_list(self, params, date_start, month_last_day, dates):
        """ Fill the list of dates given in arguments depending on the recurring parameters.
        """
        if params.of_rec_interval < 1:
            raise UserError(_("The interval between two vouchers must be at least equal to 1."))
        if params.of_rec_number < 2:
            raise UserError(_("For a recurring entry, you must request at least 2 vouchers."))

        force_day = None
        interval = params.of_rec_interval
        interval_type = params.of_rec_interval_type
        if interval_type == 'months' and date_start.day == month_last_day:
            # Les écritures seront au dernier jour du mois pour tous les mois de la récurrence.
            force_day = 31
        delta = self.get_relative_delta(recurring_rule_type=interval_type, interval=interval, day=force_day)
        next_date = date_start
        for _dummy in range(params.of_rec_number - 1):
            next_date += delta
            dates.append(next_date)
