# -*- encoding: utf-8 -*-

from datetime import date
from datetime import timedelta
from dateutil.rrule import WEEKLY
from odoo import api, models, fields


class DateRangeGenerator(models.TransientModel):
    _inherit = 'date.range.generator'

    @api.model
    def auto_genere_quinzaines(self, date_start_str=False):
        dr_type_obj = self.env['date.range.type']
        dr_type = dr_type_obj.search([('name', '=', 'Quinzaine civile')], limit=1)
        if not dr_type:
            dr_type = dr_type_obj.create({'name': 'Quinzaine civile', 'company_id': False, 'allow_overlap': False})
        if not date_start_str:
            dr = self.env['date.range'].search([('type_id', '=', dr_type.id)], order="date_start DESC", limit=1)
            if not dr:
                year_int = fields.Date.from_string(fields.Date.today()).year
                date_start_str = fields.Date.to_string(date(year_int, 1, 1))
            else:
                # le lendemain de la dernière période en date
                date_start_da = fields.Date.from_string(dr.date_end) + timedelta(days=1)
                date_start_str = fields.Date.to_string(date_start_da)

        date_start_dt = fields.Datetime.from_string(date_start_str)
        year_int = date_start_dt.year
        year_str = str(year_int % 100)
        name_prefix = "Q-%s-" % year_str
        # replacer la date de début sur un lundi pour caler les quinzaine sur des semaines
        date_start_dt -= timedelta(days=date_start_dt.weekday())

        vals = {
            'name_prefix': name_prefix,
            'date_start': fields.Date.to_string(date_start_dt),
            'type_id': dr_type.id,
            'company_id': False,
            'unit_of_time': WEEKLY,
            'duration_count': 2,
            'count': 27,
        }
        dr_gen = self.create(vals)
        date_ranges = dr_gen._compute_date_ranges()
        if date_ranges:
            # replacer la date de début de la première période sur le premier de l'an
            # pour eviter les chevauchements de périodes
            dr_first_debut_da = date(year_int, 1, 1)
            date_ranges[0]['date_start'] = fields.Date.to_string(dr_first_debut_da)
            # replacer la date de fin de la dernière période sur le 31 décembre
            # pour eviter les chevauchements de périodes
            dr_last_fin_da = date(year_int, 12, 31)
            date_ranges[-1]['date_end'] = fields.Date.to_string(dr_last_fin_da)
            for dr in date_ranges:
                self.env['date.range'].create(dr)
        return self.env['ir.actions.act_window'].for_xml_id(
            module='date_range', xml_id='date_range_action')
