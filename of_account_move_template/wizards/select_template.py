# -*- coding: utf-8 -*-

from datetime import date as dt_date
from dateutil.relativedelta import relativedelta
import calendar

from odoo import models, fields, api
from odoo.exceptions import UserError


class WizardSelectMoveTemplate(models.TransientModel):
    _inherit = "wizard.select.move.template"

    of_template_ids = fields.Many2many('account.move.template', string=u"Modèles")
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
            ('custom', u"Date choisie"),
        ],
        string=u"Extourner", default='none', required=True
    )
    of_extourne_date = fields.Date(string="Date extourne")

    @api.model
    def default_get(self, fields_list):
        result = super(WizardSelectMoveTemplate, self).default_get(fields_list)
        if 'of_template_ids' in fields_list and 'template_id' in fields_list:
            if self._context.get('active_model') == 'account.move.template':
                template_ids = self._context['active_ids'] or []
                if len(template_ids) > 1:
                    # La génération depuis des modèles multiples n'est autorisée que si ils sont entièrement calculés
                    templates = self.env['account.move.template'].browse(template_ids)\
                        .filtered(lambda t: t.template_line_ids.filtered(lambda l: l.type == 'input'))
                    if templates:
                        raise UserError(
                            u"La génération depuis plusieurs modèles simultanément nécessite qu'ils n'aient pas de "
                            u"montants en saisie manuelle.\nModèle en erreur: %s" % (templates[0].name, ))
                result['of_template_ids'] = template_ids
                result['template_id'] = template_ids and template_ids[0] or False
        return result

    @api.multi
    def load_lines(self):
        # Réécriture de la fonction pour ne pas générer automatiquement les pièces comptables
        # quand il n'y a pas de ligne à montant "manuel" et que le modèle indique une récurrence.
        self.ensure_one()
        lines = self.template_id.template_line_ids
        for line in lines.filtered(lambda l: l.type == 'input'):
            self.env['wizard.select.move.template.line'].create({
                'template_id': self.id,
                'sequence': line.sequence,
                'name': line.name,
                'amount': 0.0,
                'account_id': line.account_id.id,
                'move_line_type': line.move_line_type,
            })
        if not self.line_ids and not self.template_id.of_recurring:
            return self.load_templates()

        data = self.template_id.read(
            ['of_recurring', 'of_rec_interval', 'of_rec_interval_type', 'of_rec_number', 'of_prorata',
             'of_extourne', 'of_extourne_date'])[0]
        if data['of_extourne_date']:
            extourne_date = fields.Date.from_string(data['of_extourne_date'])
            month_start = dt_date.today() + relativedelta(day=1)
            extourne_date += relativedelta(year=month_start.year)
            if extourne_date < month_start:
                extourne_date += relativedelta(years=1)
            data['of_extourne_date'] = extourne_date
        data['state'] = 'template_selected'
        self.write(data)

        view_rec = self.env.ref('account_move_template.wizard_select_template')
        return {
            'view_type': 'form',
            'view_id': [view_rec.id],
            'view_mode': 'form',
            'res_model': 'wizard.select.move.template',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self.env.context,
        }

    @api.multi
    def load_template(self, input_lines, params, template):
        amounts = template.compute_lines(input_lines)
        totals = {sequence: 0 for sequence in amounts}
        name = template.name
        partner = self.partner_id.id
        moves = self.env['account.move']
        date_start_da = fields.Date.from_string(self.of_date_start)
        month_last_day = calendar.monthrange(date_start_da.year, date_start_da.month)[1]
        of_prorata = self.of_rec_interval_type == 'months' and self.of_prorata

        # Calcul des dates des pièces comptables.
        dates = [self.of_date_start]
        if params.of_recurring:
            if params.of_rec_interval < 1:
                raise UserError(u"L'intervalle entre deux pièces doit être au moins égal à 1.")
            if params.of_rec_number < 2:
                raise UserError(u"Pour une écriture récurrente, vous devez demander au moins 2 pièces.")
            delta = relativedelta()
            if params.of_rec_interval_type == 'months' and date_start_da.day == month_last_day:
                # Les écritures seront au dernier jour du mois pour tous les mois de la récurrence.
                delta = relativedelta(day=31)
            for _ in xrange(params.of_rec_number - 1):
                setattr(
                    delta,
                    params.of_rec_interval_type,
                    getattr(delta, params.of_rec_interval_type) + params.of_rec_interval)
                dates.append(fields.Date.to_string(date_start_da + delta))

        # Génération des pièces
        imax = len(dates) - 1
        for journal in template.template_line_ids.mapped('journal_id'):
            template_lines = template.template_line_ids.filtered(lambda j: j.journal_id == journal)

            for i, date in enumerate(dates):
                date_amounts = amounts
                if params.of_recurring:
                    if i == 0 and of_prorata:
                        ratio = float(month_last_day - date_start_da.day + 1) / month_last_day
                        date_amounts = {sequence: amount * ratio for sequence, amount in date_amounts.iteritems()}
                        amt0 = date_amounts
                    elif i == imax and of_prorata:
                        date_amounts = {
                            sequence: amount - amt0[sequence]
                            for sequence, amount in date_amounts.iteritems()
                        }

                for sequence, amount in date_amounts.iteritems():
                    totals[sequence] += amount

                lines = []
                move = self._create_move(name, journal.id, partner, template.id, date)
                moves += move
                for line in template_lines:
                    lines.append((0, 0, self._prepare_line(line, date_amounts, partner)))
                move.write({'line_ids': lines})
            if params.of_recurring and params.of_extourne != 'none':
                if params.of_extourne == 'first':
                    date = self.of_date_start
                elif params.of_extourne == 'last':
                    date = moves[-1].date
                else:
                    # Date custom
                    date = params.of_extourne_date
                lines = []
                move = self._create_move(name, journal.id, partner, template.id, date)
                moves += move
                for line in template_lines:
                    line_data = self._prepare_line(line, totals, partner)
                    line_data['credit'], line_data['debit'] = line_data['debit'], line_data['credit']
                    lines.append((0, 0, line_data))
                move.write({'line_ids': lines})
        return moves

    @api.multi
    def load_templates(self):
        self.ensure_one()
        moves = self.env['account.move']
        input_lines = {}
        name = ""
        if len(self.of_template_ids) > 1:
            for template in self.of_template_ids:
                moves += self.load_template(input_lines, template, template)
        else:
            for template_line in self.line_ids:
                input_lines[template_line.sequence] = template_line.amount
            name = " : " + self.template_id.name
            moves = self.load_template(input_lines, self, self.template_id)
        return {
            'domain': [('id', 'in', moves.ids)],
            'name': u"Pièces générées depuis le modèle%s" % name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.model
    def _create_move(self, ref, journal_id, partner_id, template_id, date=None):
        move = super(WizardSelectMoveTemplate, self)._create_move(ref, journal_id, partner_id)
        move_data = {
            'of_template_id': template_id
        }
        if date:
            move_data['date'] = date
        move.write(move_data)
        return move

    @api.model
    def _prepare_line(self, line, amounts, partner_id):
        values = super(WizardSelectMoveTemplate, self)._prepare_line(line, amounts, partner_id)

        # Retrait de la valeur 'date'.
        # C'est un champ related sur la pièce comptable, ça n'a donc pas de sens de le redéfinir à chaque écriture
        del values['date']
        return values
