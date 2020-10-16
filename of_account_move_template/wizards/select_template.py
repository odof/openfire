# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
import calendar

from odoo import models, fields, api
from odoo.exceptions import UserError


class WizardSelectMoveTemplate(models.TransientModel):
    _inherit = "wizard.select.move.template"

    of_recurring = fields.Boolean(string=u"Récurrent")
    of_rec_interval = fields.Integer(string=u"Intervalle", default=1, required=True)
    of_rec_interval_type = fields.Selection(
        [('days', u"Jours"), ('months', u"Mois"), ('years', u"Années")],
        string=u"Unité de temps", default='months', required=True)
    of_rec_number = fields.Integer(string=u"Nombre de pièces", default=12, required=True)
    of_date_start = fields.Date(string=u"Date de début", default=fields.Date.today, required=True)
    of_prorata = fields.Boolean(
        string="Prorata",
        help=u"Le montant des écritures sera ajusté au prorata du mois sur le premier et le dernier mois.")

    of_extourne = fields.Selection(
        [
            ('none', u"Pas d'extourne"),
            ('first', u"Date de départ"),
            ('last', u"Date de fin"),
        ],
        string=u"Extourner", default='none', required=True
    )

    @api.multi
    def load_template(self):
        self.ensure_one()
        input_lines = {}
        for template_line in self.line_ids:
            input_lines[template_line.sequence] = template_line.amount
        amounts = self.template_id.compute_lines(input_lines)
        totals = {sequence: 0 for sequence in amounts}
        name = self.template_id.name
        partner = self.partner_id.id
        moves = self.env['account.move']
        date_start_da = fields.Date.from_string(self.of_date_start)
        month_last_day = calendar.monthrange(date_start_da.year, date_start_da.month)[1]
        of_prorata = self.of_rec_interval_type == 'months' and self.of_prorata

        # Calcul des dates des pièces comptables.
        dates = [self.of_date_start]
        if self.of_recurring:
            if self.of_rec_interval < 1:
                raise UserError(u"L'intervalle entre deux pièces doit être au moins égal à 1.")
            if self.of_rec_number < 2:
                raise UserError(u"Pour une écriture récurrente, vous devez demander au moins 2 pièces.")
            delta = relativedelta()
            if self.of_rec_interval_type == 'months' and date_start_da.day == month_last_day:
                # Les écritures seront au dernier jour du mois pour tous les mois de la récurrence.
                delta = relativedelta(day=31)
            for _ in xrange(self.of_rec_number - 1):
                setattr(
                    delta,
                    self.of_rec_interval_type,
                    getattr(delta, self.of_rec_interval_type) + self.of_rec_interval)
                dates.append(fields.Date.to_string(date_start_da + delta))

        # Génération des pièces
        imax = len(dates) - 1
        for journal in self.template_id.template_line_ids.mapped('journal_id'):
            template_lines = self.template_id.template_line_ids.filtered(lambda j: j.journal_id == journal)

            for i, date in enumerate(dates):
                date_amounts = amounts
                if self.of_recurring:
                    if i == 0 and of_prorata:
                        ratio = float(month_last_day - date_start_da.day + 1) / month_last_day
                        date_amounts = {sequence: amount * ratio for sequence, amount in date_amounts.iteritems()}
                    elif i == imax and of_prorata:
                        date_da = fields.Date.from_string(date)
                        ratio = float(date_da.day - 1) / calendar.monthrange(date_da.year, date_da.month)[1]
                        date_amounts = {sequence: amount * ratio for sequence, amount in date_amounts.iteritems()}

                for sequence, amount in date_amounts.iteritems():
                    totals[sequence] += amount

                lines = []
                move = self._create_move(name, journal.id, partner, date)
                moves += move
                for line in template_lines:
                    lines.append((0, 0, self._prepare_line(line, date_amounts, partner)))
                move.write({'line_ids': lines})
            if self.of_extourne != 'none':
                if self.of_extourne == 'first':
                    date = self.of_date_start
                else:
                    date = moves[-1].date
                lines = []
                move = self._create_move(name, journal.id, partner, date)
                moves += move
                for line in template_lines:
                    line_data = self._prepare_line(line, totals, partner)
                    line_data['credit'], line_data['debit'] = line_data['debit'], line_data['credit']
                    lines.append((0, 0, line_data))
                move.write({'line_ids': lines})

        return {
            'domain': [('id', 'in', moves.ids)],
            'name': 'Entries from template: %s' % name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.model
    def _create_move(self, ref, journal_id, partner_id, date=None):
        # Choix de la date dans la pièce comptable
        move = super(WizardSelectMoveTemplate, self)._create_move(ref, journal_id, partner_id)
        if date:
            move.date = date
        return move

    @api.model
    def _prepare_line(self, line, amounts, partner_id):
        values = super(WizardSelectMoveTemplate, self)._prepare_line(line, amounts, partner_id)

        # Retrait de la valeur 'date'.
        # C'est un champ related sur la pièce comptable, ça n'a donc pas de sens de le redéfinir à chaque écriture
        del values['date']
        return values
