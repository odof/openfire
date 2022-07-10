# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api


class OfSaleOrderKanban(models.Model):
    _name = 'of.sale.order.kanban'
    _description = u"Étapes kanban des sale.order"
    _order = 'sequence, id'

    @api.model_cr_context
    def _auto_init(self):
        res = super(OfSaleOrderKanban, self)._auto_init()
        ir_config_obj = self.env['ir.config_parameter']
        kanban_new = self.env.ref('of_sale_kanban.of_sale_order_kanban_new', raise_if_not_found=False)
        existing_kanban = self.search(kanban_new and [('id', '!=', kanban_new.id)] or [])
        if not ir_config_obj.get_param('of.sale.order.kanban.data.loaded') and not existing_kanban:
            for name in [
                    u'Validation technique', u'Approvisionnement', u'Prêt à poser',
                    u'Suivi de pose', u'Terminé']:
                self.create({'name': name})
        if not ir_config_obj.get_param('of.sale.order.kanban.data.loaded'):
            ir_config_obj.set_param('of.sale.order.kanban.data.loaded', 'True')
        return res

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string=u"Nom de l'étape", required=True)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_kanban_step_id = fields.Many2one(
        comodel_name='of.sale.order.kanban', string=u"Étape kanban",
        default=lambda s: s.env.ref('of_sale_kanban.of_sale_order_kanban_new', raise_if_not_found=False),
        group_expand='_read_group_kanban_step_ids', track_visibility='onchange'
    )
    # fields used for the kanban view
    of_notes_display = fields.Text(string='Notes for display', compute='_of_compute_values_to_display')
    of_info_display = fields.Text(string='Infos for display', compute='_of_compute_values_to_display')
    of_nbr_overdue_activities = fields.Char(
        string="Number of overdue activities", compute='_of_compute_values_to_display')
    of_overdue_activities = fields.Text(string="Overdue activities", compute='_of_compute_values_to_display')

    @api.model
    def function_set_kanban_step_id(self):
        step = self.env.ref('of_sale_kanban.of_sale_order_kanban_new', raise_if_not_found=False)
        if step:
            self._cr.execute('UPDATE sale_order SET of_kanban_step_id = %s', (step.id,))

    @api.multi
    def _of_compute_values_to_display(self):
        for rec in self:
            # notes and information
            list_notes = rec.of_notes.split('\n') if rec.of_notes else []
            list_info = rec.of_info.split('\n') if rec.of_info else []
            rec.of_notes_display = json.dumps(list_notes) if list_notes else False
            rec.of_info_display = json.dumps(list_info) if list_info else False

            # activities
            overdue_activities = rec._of_get_overdue_activities()
            activities = []
            for activity in overdue_activities:
                if len(activities) < 3:
                    activities.append(activity.type_id.of_short_name)
                else:
                    activities.append("...")
                    break
            rec.of_overdue_activities = json.dumps(activities) if activities else False
            rec.of_nbr_overdue_activities = "(%s/%s)" % (
                len(overdue_activities), len(rec.of_crm_activity_ids))

    @api.model
    def _read_group_kanban_step_ids(self, stages, domain, order):
        kanban_step_ids = self.env['of.sale.order.kanban'].search([])
        return kanban_step_ids
