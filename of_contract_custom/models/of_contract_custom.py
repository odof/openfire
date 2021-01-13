# -*- coding: utf-8 -*-

from odoo import models, fields, api


# class OfContractTemplate(models.Model):
#     _name = "of.contract.template"
#
#     name = fields.Char(required=True)
#     pricelist_id = fields.Many2one('product.pricelist', string='Liste de prix',)
#     line_ids = fields.One2many('of.contract.line', 'contract_template_id', string='Services')
#     recurring_rule_type = fields.Selection([
#         ('date', u'À la prestation'),
#         ('month', 'Mensuelle'),
#         ('trimester', u'Trimestrielle'),  # Tout les 3 mois
#         ('semester', u'Semestrielle'),  # 2 fois par ans
#         ('year', u'Annuelle'),
#         ], default='month', string=u"Fréquence de facturation", help="Interval de temps entre chaque facturation",
#         required=True
#     )
#     recurring_invoicing_payment = fields.Selection(
#         [('pre-paid', u'À échoir'),
#          ('post-paid', u'Échu'),
#          ], default='pre-paid', string='Type de facturation', help="Specify if process date is 'from' or 'to' invoicing date")
#     journal_id = fields.Many2one('account.journal', string='Journal', default=lambda s: s._default_journal(), domain="[('type', '=', 'sale'),('company_id', '=', company_id)]")
#     fiscal_position_id = fields.Many2one('account.fiscal.position', string="Position fiscale")
#
#     @api.model
#     def _default_journal(self):
#         company_id = self.env.context.get(
#             'company_id', self.env.user.company_id.id)
#         domain = [
#             ('type', '=', 'sale'),
#             ('company_id', '=', company_id)]
#         return self.env['account.journal'].search(domain, limit=1)


# class DateRange(models.Model):
#     _inherit = 'date.range'
#
#     @api.model
#     def generate_contract_date_range(self):
#         today = date.today()
#
#         first_day = today + relativedelta(month=1, day=1)
#         for i in xrange(0, 10):
#             last_day = first_day + relativedelta(years=1, days=-1)
#             type_id = self.env.ref('of_contract_custom.of_contract_custom_date_range_type').id
#             exist = bool(self.search([('date_start','=', first_day), ('date_end','=',last_day), ('type_id','=',type_id)]))
#             if not exist:
#                 self.create({
#                     'name': u"Année %s" % first_day.strftime("%Y"),
#                     'date_start': fields.Date.to_string(first_day),
#                     'date_end': fields.Date.to_string(last_day),
#                     'type_id': type_id,
#                     'company_id': False,
#                 })
#             first_day = first_day + relativedelta(years=1)
