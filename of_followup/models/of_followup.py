# -*- coding: utf-8 -*-

from datetime import datetime, date
import json

from odoo import api, fields, models
from odoo.addons.muk_dms.models import dms_base

AVAILABLE_PRIORITIES = [
    ('0', u'Normal'),
    ('1', u'Basse'),
    ('2', u'Haute'),
    ('3', u'Très haute'),
]


class OFFollowupProject(models.Model):
    _name = 'of.followup.project'
    _inherit = 'mail.thread'
    _description = "Suivi des projets"
    _order = "priority desc, reference_laying_date, id desc"

    stage_id = fields.Many2one(
        comodel_name='of.followup.project.stage', string=u"Etape de suivi", required=True, readonly=True,
        group_expand='_read_group_stage_ids')
    state = fields.Selection(
        [('in_progress', u'En cours'),
         ('late', u'En retard'),
         ('ready', u'Prêt'),
         ('done', u'Terminé'),
         ('cancel', u'Annulé')],
        string=u"Etat du dossier", compute='_compute_state', search='_search_state')
    is_done = fields.Boolean(string=u"Est terminé")
    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", required=True, copy=False)
    partner_id = fields.Many2one(related='order_id.partner_id', string=u"Client", readonly=True)
    intervention_address_id = fields.Many2one(
        related='order_id.partner_shipping_id', string=u"Adresse d'intervention", readonly=True)
    invoice_status = fields.Selection(related='order_id.invoice_status', string=u"État de facturation", readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string=u"Responsable", default=lambda self: self.env.user)
    reference_laying_date = fields.Date(string=u"Date de pose de référence")
    laying_week = fields.Char(string=u"Semaine de pose", compute='_compute_laying_week')
    task_ids = fields.One2many(comodel_name='of.followup.task', inverse_name='project_id', string=u"Tâches")
    predefined_task_ids = fields.One2many(
        comodel_name='of.followup.task', inverse_name='project_id', string=u"Tâches pré-définies",
        domain=[('predefined_task', '=', True)])
    other_task_ids = fields.One2many(
        comodel_name='of.followup.task', inverse_name='project_id', string=u"Autres tâches",
        domain=[('predefined_task', '=', False)])
    template_id = fields.Many2one(comodel_name='of.followup.project.template', string=u"Modèle")
    color = fields.Char(string=u"Couleur", compute="_compute_color")
    priority = fields.Selection(AVAILABLE_PRIORITIES, string='Rating', index=True, default=AVAILABLE_PRIORITIES[0][0])
    info = fields.Text(string=u"Infos")
    notes = fields.Text(string=u"Notes")
    tag_ids = fields.Many2many(comodel_name='of.followup.project.tag', string=u"Étiquettes")
    alert_ids = fields.Many2many(
        comodel_name='of.followup.project.alert', string=u"Alertes", compute='_compute_alert_ids')

    invoice_count = fields.Integer(string=u"Nombre de factures", related='order_id.invoice_count', readonly=True)
    purchase_count = fields.Integer(string=u"Nombre d'achats", related='order_id.purchase_count', readonly=True)
    intervention_count = fields.Integer(
        string=u"Nombre d'interventions", related='order_id.intervention_count', readonly=True)
    to_schedule_count = fields.Integer(
        string=u"Nombre d'interventions à programmer", related='order_id.of_a_programmer_count', readonly=True)
    delivery_count = fields.Integer(string=u"Nombre de livraisons", related='order_id.delivery_count', readonly=True)
    picking_count = fields.Integer(string=u"Nombre de réceptions", compute='_compute_picking_count')

    # Champs pour affichage vignette kanban
    late_tasks_number = fields.Char(string=u"Nombre de tâches en retard", compute='_compute_late_tasks_number')
    late_tasks = fields.Text(string=u"Tâches en retard", compute='_compute_late_tasks')
    info_display = fields.Text(string=u"Infos pour affichage", compute='_compute_info_display')
    date_alert_display = fields.Text(string=u"Infos pour alerte de dates", compute='_compute_alert_display')
    picking_alert_display = fields.Text(
        string=u"Infos pour alerte de livraison/réception", compute='_compute_alert_display')

    _sql_constraints = [('order_uniq', 'unique (order_id)', u"Un suivi a déjà été créé pour cette commande !")]

    @api.multi
    def name_get(self):
        res = []
        for followup in self:
            name = "Suivi commande %s" % followup.order_id.name
            res.append((followup.id, name))
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        stage_ids = self.env['of.followup.project.stage'].search([])
        return stage_ids

    @api.multi
    def _compute_state(self):
        for rec in self:
            # Si commande annulée, le suivi est à l'état annulé également
            if rec.order_id.state == 'cancel':
                rec.state = 'cancel'
            else:
                # Par défaut le projet est en cours
                state = 'in_progress'
                # Le projet a été marqué comme terminé
                if rec.is_done:
                    state = 'done'
                else:
                    # Toutes les tâches sont terminées (excepté les non traitées)
                    if rec.task_ids and not rec.task_ids.filtered(lambda t: not t.is_not_processed).\
                            filtered(lambda t: not t.is_done):
                        state = 'ready'
                    # Au moins une tâche est en retard
                    elif rec.task_ids.filtered(lambda t: t.is_late):
                        state = 'late'
                rec.state = state

    @api.model
    def _search_state(self, operator, value):
        if operator == '=':
            followups = self.search([]).filtered(lambda f: f.state == value)
            return [('id', 'in', followups.ids)]

    @api.multi
    def _compute_laying_week(self):
        for rec in self:
            if rec.reference_laying_date:
                laying_week = datetime.strptime(rec.reference_laying_date, "%Y-%m-%d").date().isocalendar()[1]
                rec.laying_week = "%02d" % laying_week
            else:
                rec.laying_week = "Non programmé"

    @api.multi
    def _compute_color(self):
        for rec in self:
            state = rec.state
            if state == 'in_progress':
                color = '#ffffff'
            elif state == 'late':
                color = '#ffa8a8'
            elif state == 'ready':
                color = '#bcffa8'
            elif state == 'done':
                color = '#d7d7d7'
            elif state == 'cancel':
                color = '#eeeeee'
            else:
                color = '#ffffff'
            rec.color = color

    @api.multi
    def _compute_alert_ids(self):
        for rec in self:
            if rec.order_id:
                alerts = self.env['of.followup.project.alert']
                # Vérification des dates
                planif_task_type = self.env.ref('of_followup.of_followup_task_type_planif')
                if planif_task_type and rec.reference_laying_date:
                    planif_planning_tache_categs = planif_task_type.planning_tache_categ_ids
                    interventions = rec.order_id.intervention_ids.filtered(
                        lambda i: i.tache_id.tache_categ_id.id in planif_planning_tache_categs.ids)
                    if interventions.filtered(lambda i: i.date_date > rec.reference_laying_date):
                        alerts |= self.env.ref('of_followup.of_followup_project_alert_date')
                    else:
                        interventions_to_schedule = rec.order_id.of_a_programmer_ids.filtered(
                            lambda i: i.tache_id.tache_categ_id.id in planif_planning_tache_categs.ids)
                        if interventions_to_schedule.filtered(lambda i: i.date_next > rec.reference_laying_date):
                            alerts |= self.env.ref('of_followup.of_followup_project_alert_date')
                # Vérification BL
                if rec.order_id.picking_ids:
                    late_delivery_pickings = rec.order_id.picking_ids.filtered(
                        lambda p: p.state != 'done' and p.min_date < fields.Datetime.now())
                    if late_delivery_pickings:
                        alerts |= self.env.ref('of_followup.of_followup_project_alert_bl')
                # Vérification BR
                if rec.order_id.purchase_ids.mapped('picking_ids'):
                    late_receipt_pickings = rec.order_id.purchase_ids.mapped('picking_ids').filtered(
                        lambda p: p.state != 'done' and p.min_date < fields.Datetime.now())
                    if late_receipt_pickings:
                        alerts |= self.env.ref('of_followup.of_followup_project_alert_br')
                rec.alert_ids = alerts

    @api.multi
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = sum(rec.order_id.purchase_ids.mapped('picking_count'))

    @api.multi
    def _compute_late_tasks_number(self):
        for rec in self:
            rec.late_tasks_number = "(%s/%s)" % (len(rec.task_ids.filtered(lambda t: t.is_late)), len(rec.task_ids))

    @api.multi
    def _compute_late_tasks(self):
        for rec in self:
            late_tasks = []
            for late_task in rec.task_ids.filtered(lambda t: t.is_late):
                if len(late_tasks) < 3:
                    late_tasks.append(late_task.type_id.short_name)
                else:
                    late_tasks.append("...")
                    break
            rec.late_tasks = json.dumps(late_tasks) if late_tasks else False

    @api.multi
    def _compute_info_display(self):
        for rec in self:
            info = []
            if rec.info:
                for line in rec.info.split('\n'):
                    info.append(line)
            rec.info_display = json.dumps(info) if info else False

    @api.multi
    def _compute_alert_display(self):
        for rec in self:
            date_alert = []
            picking_alert = []
            if rec.alert_ids:
                for alert in rec.alert_ids:
                    if alert == self.env.ref('of_followup.of_followup_project_alert_date'):
                        date_alert.append(alert.name)
                    else:
                        picking_alert.append(alert.name)
            rec.date_alert_display = json.dumps(date_alert) if date_alert else False
            rec.picking_alert_display = json.dumps(picking_alert) if picking_alert else False

    @api.model
    def get_color(self):
        state = self.state
        if state == 'in_progress':
            return 1
        elif state == 'late':
            return 2
        elif state == 'ready':
            return 3
        elif state == 'done':
            return 4
        else:
            return 0

    def get_stage(self, laying_date):
        if laying_date:
            laying_date = datetime.strptime(laying_date, "%Y-%m-%d").date()
            today = date.today()
            if laying_date < today:
                return self.env['of.followup.project.stage'].search([('code', '=', 's+')], limit=1)
            else:
                week_diff = laying_date.isocalendar()[1] - today.isocalendar()[1]
                return self.env['of.followup.project.stage'].search(
                    [('week_diff_min', '<=', week_diff), ('week_diff_max', '>=', week_diff)], limit=1)
        else:
            return self.env['of.followup.project.stage'].search([('code', '=', 'coming')], limit=1)

    def get_reference_laying_date(self):
        if self.order_id:
            planif_task_type = self.env.ref('of_followup.of_followup_task_type_planif')
            if planif_task_type:
                planif_planning_tache_categs = planif_task_type.planning_tache_categ_ids
                interventions = self.order_id.intervention_ids.filtered(
                    lambda i: i.tache_id.tache_categ_id.id in planif_planning_tache_categs.ids)
                if interventions:
                    intervention = interventions[0]
                    return intervention.date
                else:
                    interventions_to_schedule = self.order_id.of_a_programmer_ids.filtered(
                        lambda i: i.tache_id.tache_categ_id.id in planif_planning_tache_categs.ids)
                    if interventions_to_schedule:
                        intervention_to_schedule = interventions_to_schedule[0]
                        return intervention_to_schedule.date_next
        return False

    @api.model
    def create(self, vals):
        if 'reference_laying_date' in vals:
            reference_laying_date = vals.get('reference_laying_date', False)
            stage = self.get_stage(reference_laying_date)
            vals.update({'stage_id': stage.id})
        return super(OFFollowupProject, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'reference_laying_date' in vals:
            reference_laying_date = vals.get('reference_laying_date', False)
            stage = self.get_stage(reference_laying_date)
            vals.update({'stage_id': stage.id})
        return super(OFFollowupProject, self).write(vals)

    @api.multi
    def set_to_done(self):
        self.ensure_one()
        self.is_done = True

    @api.multi
    def set_to_in_progress(self):
        self.ensure_one()
        self.is_done = False

    @api.multi
    def action_send_email(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('of_followup', 'of_followup_project_email_template')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'of.followup.project',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_partner_ids': self.partner_id.ids,
            'default_composition_mode': 'comment',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def update_laying_date(self):
        self.ensure_one()
        new_laying_date = self.get_reference_laying_date()
        if new_laying_date:
            self.reference_laying_date = new_laying_date

    @api.model
    def cron_move_project(self):
        for project in self.search([]):
            project.write({'stage_id': self.get_stage(project.reference_laying_date).id})

    @api.onchange('order_id')
    def onchange_order_id(self):
        self.reference_laying_date = self.get_reference_laying_date()

    @api.onchange('template_id')
    def onchange_template_id(self):
        if not self.template_id:
            return
        new_tasks = []
        for task in self.template_id.task_ids:
            vals = {'sequence': task.sequence, 'type_id': task.type_id.id, 'name': task.name}
            state = self.env['of.followup.task.type.state'].search(
                [('task_type_id', '=', task.type_id.id), ('starting_state', '=', True)], limit=1)
            if state:
                if task.predefined_task:
                    vals.update({'predefined_state_id': state.id})
                else:
                    vals.update({'state_id': state.id})
            new_tasks += [(0, 0, vals)]
        return {'value': {'task_ids': new_tasks}}

    @api.multi
    def action_view_invoice(self):
        self.ensure_one()
        return self.order_id.action_view_invoice()

    @api.multi
    def action_view_purchase(self):
        self.ensure_one()
        return self.order_id.action_view_achats()

    @api.multi
    def action_view_interventions(self):
        self.ensure_one()
        return self.order_id.action_view_interventions()

    @api.multi
    def action_view_to_schedule(self):
        self.ensure_one()
        return self.order_id.action_view_a_programmer()

    @api.multi
    def action_view_delivery(self):
        self.ensure_one()
        return self.order_id.action_view_delivery()

    @api.multi
    def action_view_picking(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        pick_ids = self.order_id.purchase_ids.mapped('picking_ids').ids or []
        if len(pick_ids) > 1:
            result['domain'] = "[('id', 'in', [" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result


class OFFollowupProjectStage(models.Model):
    _name = 'of.followup.project.stage'
    _description = "Etat de suivi des projets"
    _order = 'sequence'

    name = fields.Char(string=u"Nom")
    code = fields.Char(string=u"Code")
    sequence = fields.Integer(string=u"Séquence")
    fold = fields.Boolean(string=u"Replié par défaut")

    week_diff_min = fields.Integer(string=u"Différence de semaine minimale")
    week_diff_max = fields.Integer(string=u"Différence de semaine maximale")


class OFFollowupTask(models.Model):
    _name = 'of.followup.task'
    _description = u"Tâche liée au suivi des projets"
    _order = 'sequence'

    project_id = fields.Many2one(
        comodel_name="of.followup.project", string=u"Projet", required=True, ondelete='cascade')

    sequence = fields.Integer(string=u"Séquence")
    type_id = fields.Many2one(comodel_name='of.followup.task.type', string=u"Type", required=True)
    name = fields.Char(string=u"Nom", required=True)
    state_id = fields.Many2one(comodel_name='of.followup.task.type.state', string=u"Etat")
    predefined_state_id = fields.Many2one(
        comodel_name='of.followup.task.type.state', string=u"Etat", compute='_compute_predefined_state_id')
    global_state = fields.Char(string=u"État", compute='_compute_global_state')
    predefined_task = fields.Boolean(string=u"Tâche pré-définie", related='type_id.predefined_task')
    force_state = fields.Boolean(string=u"Gestion manuelle de l'état")
    is_late = fields.Boolean(string=u"Tâche en retard", compute='_compute_is_late')
    is_done = fields.Boolean(string=u"Tâche terminée", compute='_compute_is_done')
    is_not_processed = fields.Boolean(string=u"Tâche non traitée", compute='_compute_is_not_processed')
    planif_intervention_ids = fields.One2many(
        comodel_name='of.planning.intervention', string=u"RDVs d'intervention planifiés",
        compute='_compute_planif_intervention_ids')
    display_planif_interventions = fields.Boolean(
        string=u"Afficher les RDVs d'intervention planifiés ?", compute='_compute_planif_intervention_ids')
    vt_intervention_ids = fields.One2many(
        comodel_name='of.planning.intervention', string=u"RDVs visite technique",
        compute='_compute_vt_intervention_ids')
    display_vt_interventions = fields.Boolean(
        string=u"Afficher les RDVs visite technique ?", compute='_compute_vt_intervention_ids')
    app_order_line_ids = fields.One2many(
        comodel_name='sale.order.line', string=u"Lignes de commande appareils", compute='_compute_app_order_line_ids')
    display_app_order_lines = fields.Boolean(
        string=u"Afficher les lignes de commande appareils ?", compute='_compute_app_order_line_ids')
    acc_order_line_ids = fields.One2many(
        comodel_name='sale.order.line', string=u"Lignes de commande accessoires", compute='_compute_acc_order_line_ids')
    display_acc_order_lines = fields.Boolean(
        string=u"Afficher les lignes de commande accessoires ?", compute='_compute_acc_order_line_ids')
    app_picking_line_ids = fields.One2many(
        comodel_name='stock.move', string=u"Lignes de BL appareils", compute='_compute_app_picking_line_ids')
    display_app_picking_lines = fields.Boolean(
        string=u"Afficher les lignes de BL appareils ?", compute='_compute_app_picking_line_ids')
    acc_picking_line_ids = fields.One2many(
        comodel_name='stock.move', string=u"Lignes de BL accessoires", compute='_compute_acc_picking_line_ids')
    display_acc_picking_lines = fields.Boolean(
        string=u"Afficher les lignes de BL accessoires ?", compute='_compute_acc_picking_line_ids')

    @api.multi
    def _compute_predefined_state_id(self):
        for rec in self:
            if not rec.type_id.state_ids or not rec.type_id.state_ids.filtered(lambda s: s.starting_state):
                continue
            rec.predefined_state_id = rec.type_id.state_ids.filtered(lambda s: s.starting_state)[0]
            # Planification
            if rec.type_id == self.env.ref('of_followup.of_followup_task_type_planif'):
                interventions = rec.planif_intervention_ids
                # Il existe des RDV d'intervention et ils sont tous au statut 'Réalisé'
                if interventions and not interventions.filtered(lambda i: i.state != 'done'):
                    rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_planif_03')
                #  Il existe au moins un RDV d'intervention au statut 'Confirmé'
                elif interventions.filtered(lambda i: i.state == 'confirm'):
                    rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_planif_02')
            # Visite technique
            elif rec.type_id == self.env.ref('of_followup.of_followup_task_type_vt'):
                interventions = rec.vt_intervention_ids
                # Il existe un RDV d'intervention de tâche "VT" au statut 'Réalisé'
                if interventions.filtered(lambda i: i.state == 'done'):
                    rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_vt_03')
                #  Il existe un RDV d'intervention de tâche "VT" au statut 'Confirmé'
                elif interventions.filtered(lambda i: i.state == 'confirm'):
                    rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_vt_02')
            # Appareils
            elif rec.type_id == self.env.ref('of_followup.of_followup_task_type_app'):
                app_order_lines = rec.app_order_line_ids
                po_validated = bool(app_order_lines)
                receipt_validated = bool(app_order_lines)
                # Non kit
                for app_order_line in app_order_lines.filtered(lambda l: not l.of_is_kit):
                    stock_moves = app_order_line.procurement_ids.mapped('move_ids')
                    # On regarde d'abord si les articles sont déjà en stock/réservés
                    qty = sum(self.env['stock.quant'].search([('reservation_id', 'in', stock_moves.ids)]).mapped('qty'))
                    if qty < app_order_line.product_uom_qty:
                        # On récupère la(les) ligne(s) de commande d'achat validée associée(s)
                        purchase_procurement_orders = self.env['procurement.order'].search(
                            [('move_dest_id', 'in', stock_moves.ids)])
                        validated_purchase_lines = purchase_procurement_orders.mapped('purchase_line_id').filtered(
                            lambda l: l.order_id.state == 'purchase')
                        # On contrôle que les quantités commandées correspondent
                        if app_order_line.product_uom_qty - qty <= sum(validated_purchase_lines.mapped('product_qty')):
                            receipts = validated_purchase_lines.mapped('order_id').mapped('picking_ids')
                            if not receipts or receipts != receipts.filtered(lambda r: r.state == 'done'):
                                receipt_validated = False
                        else:
                            po_validated = False
                            break
                # Kit
                for app_order_line in app_order_lines.filtered(lambda l: l.of_is_kit):
                    for kit_line in app_order_line.kit_id.kit_line_ids.filtered(
                            lambda l: l.product_id.type == 'product'):
                        stock_moves = kit_line.procurement_ids.mapped('move_ids')
                        # On regarde d'abord si les articles sont déjà en stock/réservés
                        qty = sum(
                            self.env['stock.quant'].search([('reservation_id', 'in', stock_moves.ids)]).mapped('qty'))
                        if qty < kit_line.qty_per_kit:
                            # On récupère la(les) ligne(s) de commande d'achat validée associée(s)
                            purchase_procurement_orders = self.env['procurement.order'].search(
                                [('move_dest_id', 'in', stock_moves.ids)])
                            validated_purchase_lines = purchase_procurement_orders.mapped('purchase_line_id').filtered(
                                lambda l: l.order_id.state == 'purchase')
                            # On contrôle que les quantités commandées correspondent
                            if kit_line.qty_per_kit - qty <= sum(validated_purchase_lines.mapped('product_qty')):
                                receipts = validated_purchase_lines.mapped('order_id').mapped('picking_ids')
                                if not receipts or receipts != receipts.filtered(lambda r: r.state == 'done'):
                                    receipt_validated = False
                            else:
                                po_validated = False
                                break
                if not app_order_lines:
                    rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_np')
                else:
                    if po_validated:
                        if receipt_validated:
                            rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_app_03')
                        else:
                            rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_app_02')
            # Accessoires
            elif rec.type_id == self.env.ref('of_followup.of_followup_task_type_acc'):
                acc_order_lines = rec.acc_order_line_ids
                po_validated = bool(acc_order_lines)
                receipt_validated = bool(acc_order_lines)
                # Non kit
                for acc_order_line in acc_order_lines.filtered(lambda l: not l.of_is_kit):
                    stock_moves = acc_order_line.procurement_ids.mapped('move_ids')
                    # On regarde d'abord si les articles sont déjà en stock/réservés
                    qty = sum(self.env['stock.quant'].search([('reservation_id', 'in', stock_moves.ids)]).mapped('qty'))
                    if qty < acc_order_line.product_uom_qty:
                        # On récupère la(les) ligne(s) de commande d'achat validée associée(s)
                        purchase_procurement_orders = self.env['procurement.order'].search(
                            [('move_dest_id', 'in', stock_moves.ids)])
                        validated_purchase_lines = purchase_procurement_orders.mapped('purchase_line_id').filtered(
                            lambda l: l.order_id.state == 'purchase')
                        # On contrôle que les quantités commandées correspondent
                        if acc_order_line.product_uom_qty - qty <= sum(validated_purchase_lines.mapped('product_qty')):
                            receipts = validated_purchase_lines.mapped('order_id').mapped('picking_ids')
                            if not receipts or receipts != receipts.filtered(lambda r: r.state == 'done'):
                                receipt_validated = False
                        else:
                            po_validated = False
                            break
                # Kit
                for acc_order_line in acc_order_lines.filtered(lambda l: l.of_is_kit):
                    for kit_line in acc_order_line.kit_id.kit_line_ids.filtered(
                            lambda l: l.product_id.type == 'product'):
                        stock_moves = kit_line.procurement_ids.mapped('move_ids')
                        # On regarde d'abord si les articles sont déjà en stock/réservés
                        qty = sum(
                            self.env['stock.quant'].search([('reservation_id', 'in', stock_moves.ids)]).mapped('qty'))
                        if qty < kit_line.qty_per_kit:
                            # On récupère la(les) ligne(s) de commande d'achat validée associée(s)
                            purchase_procurement_orders = self.env['procurement.order'].search(
                                [('move_dest_id', 'in', stock_moves.ids)])
                            validated_purchase_lines = purchase_procurement_orders.mapped('purchase_line_id').filtered(
                                lambda l: l.order_id.state == 'purchase')
                            # On contrôle que les quantités commandées correspondent
                            if kit_line.qty_per_kit - qty <= sum(validated_purchase_lines.mapped('product_qty')):
                                receipts = validated_purchase_lines.mapped('order_id').mapped('picking_ids')
                                if not receipts or receipts != receipts.filtered(lambda r: r.state == 'done'):
                                    receipt_validated = False
                            else:
                                po_validated = False
                                break
                if not acc_order_lines:
                    rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_np')
                else:
                    if po_validated:
                        if receipt_validated:
                            rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_app_03')
                        else:
                            rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_app_02')
            # Appareils hors commande
            elif rec.type_id == self.env.ref('of_followup.of_followup_task_type_out_app'):
                app_picking_lines = rec.app_picking_line_ids
                po_validated = bool(app_picking_lines)
                receipt_validated = bool(app_picking_lines)
                for app_picking_line in app_picking_lines:
                    # On regarde d'abord si les articles sont déjà en stock/réservés
                    qty = sum(self.env['stock.quant'].search([('reservation_id', '=', app_picking_line.id)]).
                              mapped('qty'))
                    if qty < app_picking_line.product_uom_qty:
                        # On récupère la(les) ligne(s) de commande d'achat validée associée(s)
                        purchase_procurement_orders = self.env['procurement.order'].search(
                            [('move_dest_id', '=', app_picking_line.id)])
                        validated_purchase_lines = purchase_procurement_orders.mapped('purchase_line_id').filtered(
                            lambda l: l.order_id.state == 'purchase')
                        # On contrôle que les quantités commandées correspondent
                        if app_picking_line.product_uom_qty - qty <= sum(validated_purchase_lines.
                                                                         mapped('product_qty')):
                            receipts = validated_purchase_lines.mapped('order_id').mapped('picking_ids')
                            if not receipts or receipts != receipts.filtered(lambda r: r.state == 'done'):
                                receipt_validated = False
                        else:
                            po_validated = False
                            break
                if not app_picking_lines:
                    rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_np')
                else:
                    if po_validated:
                        if receipt_validated:
                            rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_out_app_03')
                        else:
                            rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_out_app_02')
            # Accessoires hors commande
            elif rec.type_id == self.env.ref('of_followup.of_followup_task_type_out_acc'):
                acc_picking_lines = rec.acc_picking_line_ids
                po_validated = bool(acc_picking_lines)
                receipt_validated = bool(acc_picking_lines)
                for acc_picking_line in acc_picking_lines:
                    # On regarde d'abord si les articles sont déjà en stock/réservés
                    qty = sum(self.env['stock.quant'].search([('reservation_id', '=', acc_picking_line.id)]).
                              mapped('qty'))
                    if qty < acc_picking_line.product_uom_qty:
                        # On récupère la(les) ligne(s) de commande d'achat validée associée(s)
                        purchase_procurement_orders = self.env['procurement.order'].search(
                            [('move_dest_id', '=', acc_picking_line.id)])
                        validated_purchase_lines = purchase_procurement_orders.mapped('purchase_line_id').filtered(
                            lambda l: l.order_id.state == 'purchase')
                        # On contrôle que les quantités commandées correspondent
                        if acc_picking_line.product_uom_qty - qty <= sum(validated_purchase_lines.
                                                                         mapped('product_qty')):
                            receipts = validated_purchase_lines.mapped('order_id').mapped('picking_ids')
                            if not receipts or receipts != receipts.filtered(lambda r: r.state == 'done'):
                                receipt_validated = False
                        else:
                            po_validated = False
                            break
                if not acc_picking_lines:
                    rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_np')
                else:
                    if po_validated:
                        if receipt_validated:
                            rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_out_acc_03')
                        else:
                            rec.predefined_state_id = self.env.ref('of_followup.of_followup_task_type_state_out_acc_02')

    @api.multi
    @api.depends('state_id', 'predefined_state_id', 'predefined_task', 'force_state')
    def _compute_global_state(self):
        for rec in self:
            if rec.predefined_task and not rec.force_state:
                rec.global_state = rec.predefined_state_id.name
            else:
                rec.global_state = rec.state_id and rec.state_id.name or ""

    @api.multi
    def _compute_is_late(self):
        not_processed_state = self.env.ref('of_followup.of_followup_task_type_state_np')
        for rec in self:
            if rec.predefined_task and not rec.force_state and rec.predefined_state_id == not_processed_state:
                rec.is_late = False
            else:
                if rec.predefined_task and not rec.force_state:
                    late_stage = rec.predefined_state_id.stage_id
                else:
                    late_stage = rec.state_id.stage_id
                if late_stage and late_stage.sequence <= rec.project_id.stage_id.sequence:
                    rec.is_late = True
                else:
                    rec.is_late = False

    @api.multi
    def _compute_is_done(self):
        not_processed_state = self.env.ref('of_followup.of_followup_task_type_state_np')
        for rec in self:
            if rec.predefined_task and not rec.force_state and rec.predefined_state_id == not_processed_state:
                rec.is_done = False
            else:
                if rec.predefined_task and not rec.force_state:
                    final_state = rec.predefined_state_id.final_state
                else:
                    final_state = rec.state_id.final_state
                if final_state:
                    rec.is_done = True
                else:
                    rec.is_done = False

    @api.multi
    def _compute_is_not_processed(self):
        not_processed_state = self.env.ref('of_followup.of_followup_task_type_state_np')
        for rec in self:
            if rec.predefined_task and not rec.force_state and rec.predefined_state_id == not_processed_state:
                rec.is_not_processed = True
            else:
                rec.is_not_processed = False

    @api.multi
    def _compute_planif_intervention_ids(self):
        planif_task_type = self.env.ref('of_followup.of_followup_task_type_planif')
        planning_tache_categs = planif_task_type.planning_tache_categ_ids
        for rec in self:
            if rec.type_id == planif_task_type:
                rec.planif_intervention_ids = rec.project_id.order_id.intervention_ids.filtered(
                    lambda i: i.tache_id.tache_categ_id.id in planning_tache_categs.ids)
                rec.display_planif_interventions = True
            else:
                rec.planif_intervention_ids = False
                rec.display_planif_interventions = False

    @api.multi
    def _compute_vt_intervention_ids(self):
        vt_task_type = self.env.ref('of_followup.of_followup_task_type_vt')
        planning_tache_categs = vt_task_type.planning_tache_categ_ids
        for rec in self:
            if rec.type_id == vt_task_type:
                rec.vt_intervention_ids = rec.project_id.order_id.intervention_ids.filtered(
                    lambda i: i.tache_id.tache_categ_id.id in planning_tache_categs.ids)
                rec.display_vt_interventions = True
            else:
                rec.vt_intervention_ids = False
                rec.display_vt_interventions = False

    @api.multi
    def _compute_app_order_line_ids(self):
        app_task_type = self.env.ref('of_followup.of_followup_task_type_app')
        product_categs = app_task_type.product_categ_ids
        for rec in self:
            if rec.type_id == app_task_type:
                rec.display_app_order_lines = True
                if rec.project_id.order_id.state == 'sale':
                    rec.app_order_line_ids = rec.project_id.order_id.order_line.filtered(
                        lambda l: l.product_id.categ_id.id in product_categs.ids and
                        (l.product_id.type == 'product' or l.of_is_kit) and l.product_uom_qty > 0)
                else:
                    rec.app_order_line_ids = False
            else:
                rec.app_order_line_ids = False
                rec.display_app_order_lines = False

    @api.multi
    def _compute_acc_order_line_ids(self):
        acc_task_type = self.env.ref('of_followup.of_followup_task_type_acc')
        app_task_type = self.env.ref('of_followup.of_followup_task_type_app')
        product_categs = app_task_type.product_categ_ids
        for rec in self:
            if rec.type_id == acc_task_type:
                rec.display_acc_order_lines = True
                if rec.project_id.order_id.state == 'sale':
                    rec.acc_order_line_ids = rec.project_id.order_id.order_line.filtered(
                        lambda l: l.product_id.categ_id.id not in product_categs.ids and
                        (l.product_id.type == 'product' or l.of_is_kit) and l.product_uom_qty > 0)
                else:
                    rec.acc_order_line_ids = False
            else:
                rec.acc_order_line_ids = False
                rec.display_acc_order_lines = False

    @api.multi
    def _compute_app_picking_line_ids(self):
        out_app_task_type = self.env.ref('of_followup.of_followup_task_type_out_app')
        product_categs = out_app_task_type.product_categ_ids
        for rec in self:
            if rec.type_id == out_app_task_type:
                rec.app_picking_line_ids = rec.project_id.order_id.picking_ids.mapped('move_lines').\
                    filtered(lambda l: not l.procurement_id and
                             l.product_id.categ_id.id in product_categs.ids and l.product_uom_qty > 0)
                rec.display_app_picking_lines = True
            else:
                rec.app_picking_line_ids = False
                rec.display_app_picking_lines = False

    @api.multi
    def _compute_acc_picking_line_ids(self):
        out_acc_task_type = self.env.ref('of_followup.of_followup_task_type_out_acc')
        out_app_task_type = self.env.ref('of_followup.of_followup_task_type_out_app')
        product_categs = out_app_task_type.product_categ_ids
        for rec in self:
            if rec.type_id == out_acc_task_type:
                rec.acc_picking_line_ids = rec.project_id.order_id.picking_ids.mapped('move_lines'). \
                    filtered(lambda l: not l.procurement_id and l.product_id.categ_id.id not in product_categs.ids and
                             l.product_uom_qty > 0)
                rec.display_acc_picking_lines = True
            else:
                rec.acc_picking_line_ids = False
                rec.display_acc_picking_lines = False

    @api.onchange('type_id')
    def _onchange_type_id(self):
        self.state_id = False
        if self.type_id and not self.predefined_task or self.force_state:
            state = self.env['of.followup.task.type.state'].search(
                [('task_type_id', '=', self.type_id.id), ('starting_state', '=', True)], limit=1)
            if state:
                self.state_id = state

    @api.multi
    def next_step(self):
        self.ensure_one()
        if self.predefined_task and not self.force_state:
            # On affiche une pop-up de confirmation
            return {
                'type': 'ir.actions.act_window',
                'name': "Avertissement !",
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'of.followup.confirm.next.step',
                'target': 'new',
            }
        else:
            # On cherche l'étape suivante
            state = self.env['of.followup.task.type.state'].search(
                [('task_type_id', '=', self.type_id.id), ('sequence', '>', self.state_id.sequence)], limit=1)
            if state:
                self.state_id = state.id
        return True

    @api.model
    def create(self, vals):
        res = super(OFFollowupTask, self).create(vals)
        # Ajout d'un message dans le chatter du projet
        self.env['mail.message'].create({
            'author_id': self.env.user.partner_id.id,
            'model': 'of.followup.project',
            'res_id': res.project_id.id,
            'type': 'comment',
            'body': u"La tâche %s a été ajoutée au suivi." % res.name,
            'date': fields.Datetime.now(),
        })
        return res

    @api.multi
    def write(self, vals):
        res = super(OFFollowupTask, self).write(vals)
        if vals.get('state_id', False):
            for rec in self:
                # Ajout d'un message dans le chatter du projet
                self.env['mail.message'].create({
                    'author_id': self.env.user.partner_id.id,
                    'model': 'of.followup.project',
                    'res_id': rec.project_id.id,
                    'type': 'comment',
                    'body': u"La tâche %s a été passée à l'état %s." % (rec.name, rec.state_id.name),
                    'date': fields.Datetime.now(),
                })
        return res

    @api.multi
    def unlink(self):
        for rec in self:
            # Ajout d'un message dans le chatter du projet
            self.env['mail.message'].create({
                'author_id': self.env.user.partner_id.id,
                'model': 'of.followup.project',
                'res_id': rec.project_id.id,
                'type': 'comment',
                'body': u"La tâche %s a été supprimée du suivi." % rec.name,
                'date': fields.Datetime.now(),
            })
        return super(OFFollowupTask, self).unlink()


class OFFollowupTaskType(models.Model):
    _name = 'of.followup.task.type'
    _description = u"Type de tâches liées au suivi des projets"

    name = fields.Char(string=u"Nom", required=True)
    short_name = fields.Char(string=u"Nom court", required=True)
    active = fields.Boolean(string=u"Actif", default=True)
    predefined_task = fields.Boolean(string=u"Tâche pré-définie", readonly=True)
    state_ids = fields.One2many(
        comodel_name='of.followup.task.type.state', inverse_name='task_type_id', string=u"Etats")
    planning_tache_categ_ids = fields.Many2many(
        comodel_name='of.planning.tache.categ', string=u"Catégories de tâches planning")
    product_categ_ids = fields.Many2many(
        comodel_name='product.category', string=u"Catégories d'articles")


class OFFollowupTaskTypeState(models.Model):
    _name = 'of.followup.task.type.state'
    _description = u"Etat des types de tâches liées au suivi des projets"
    _order = 'sequence, id desc'

    task_type_id = fields.Many2one(comodel_name='of.followup.task.type', string=u"Type de tâche", ondelete='cascade')

    sequence = fields.Integer(string=u"Séquence")
    name = fields.Char(string=u"Nom", required=True)
    starting_state = fields.Boolean(string=u"Etat de départ")
    final_state = fields.Boolean(string=u"Etat final")
    stage_id = fields.Many2one(
        comodel_name='of.followup.project.stage', string=u"En retard à partir de la période",
        domain=[('code', 'not in', ['coming', 's+'])])

    @api.model
    def create(self, vals):
        # Gestion de la séquence lors de la création
        if vals.get('task_type_id'):
            other_states = self.search([('task_type_id', '=', vals.get('task_type_id'))])
            if other_states:
                sequence = max(other_states.mapped('sequence')) + 1
            else:
                sequence = 0
            vals.update({'sequence': sequence})
        return super(OFFollowupTaskTypeState, self).create(vals)


class OFFollowupProjectTemplate(models.Model):
    _name = 'of.followup.project.template'
    _description = "Modèle de suivi des projets"

    name = fields.Char(string=u"Nom", required=True)
    task_ids = fields.One2many(comodel_name='of.followup.project.tmpl.task', inverse_name='template_id', string=u"Tâches")
    default = fields.Boolean(string=u"Modèle par défaut")


class OFFollowupProjectTmplTask(models.Model):
    _name = 'of.followup.project.tmpl.task'
    _description = u"Type de tâches liées au modèle de suivi"
    _order = 'sequence'

    template_id = fields.Many2one(comodel_name='of.followup.project.template', string=u"Modèle de suivi")
    sequence = fields.Integer(string=u"Séquence")
    type_id = fields.Many2one(comodel_name='of.followup.task.type', string=u"Type de tâche", required=True)
    predefined_task = fields.Boolean(string=u"Tâche pré-définie", related='type_id.predefined_task', readonly=True)
    name = fields.Char(string=u"Nom", related='type_id.name', readonly=True)


class OFFollowupProjectTag(models.Model):
    _name = 'of.followup.project.tag'
    _description = u"Étiquette du suivi commande"

    name = fields.Char(string=u"Nom", required=True)
    color = fields.Integer(string=u"Index couleur")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', u"Ce nom d'étiquette existe déjà !"),
    ]


class OFFollowupProjectAlert(models.Model):
    _name = 'of.followup.project.alert'
    _description = u"Alerte du suivi commande"

    name = fields.Char(string=u"Nom", required=True)
    color = fields.Integer(string=u"Index couleur", default=4)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_followup_project_id = fields.Many2one(comodel_name='of.followup.project', string=u"Suivi", copy=False)
    of_follow_count = fields.Integer(string=u"Nombre de suivi", compute='_compute_of_followup_count')

    @api.multi
    def _compute_of_followup_count(self):
        for rec in self:
            if rec.of_followup_project_id:
                rec.of_follow_count = 1
            else:
                rec.of_follow_count = 0

    @api.multi
    def action_followup_project(self):
        self.ensure_one()
        followup_project_obj = self.env['of.followup.project']
        followup_project = followup_project_obj.search([('order_id', '=', self.id)])
        if not followup_project:
            coming_stage = self.env['of.followup.project.stage'].search([('code', '=', 'coming')])
            template = self.env['of.followup.project.template'].search([('default', '=', True)])
            values = {
                'stage_id': coming_stage.id,
                'order_id': self.id,
                'template_id': template and template[0].id or False
            }
            followup_project = followup_project_obj.create(values)
            followup_project.reference_laying_date = followup_project.get_reference_laying_date()

            if followup_project.template_id:
                new_tasks = []
                for task in followup_project.template_id.task_ids:
                    vals = {'sequence': task.sequence, 'type_id': task.type_id.id, 'name': task.name}
                    state = self.env['of.followup.task.type.state'].search(
                        [('task_type_id', '=', task.type_id.id), ('starting_state', '=', True)], limit=1)
                    if state:
                        if task.predefined_task:
                            vals.update({'predefined_state_id': state.id})
                        else:
                            vals.update({'state_id': state.id})
                    new_tasks += [(0, 0, vals)]
                followup_project.task_ids = new_tasks

            self.of_followup_project_id = followup_project.id

            if self._context.get('auto_followup'):
                return True
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'of.followup.project',
                    'res_id': followup_project.id,
                    'target': 'current',
                    'flags': {'initial_mode': 'edit', 'form': {'action_buttons': True, 'options': {'mode': 'edit'}}},
                }
        else:

            if self._context.get('auto_followup'):
                return True
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'of.followup.project',
                    'res_id': followup_project.id,
                    'target': 'current',
                }

    @api.multi
    def action_confirm(self):
        super(SaleOrder, self).action_confirm()
        for order in self:
            order.with_context(auto_followup=True).action_followup_project()
        return True

    @api.multi
    def action_view_followup(self):
        self.ensure_one()
        action = self.env.ref('of_followup.of_followup_project_action').read()[0]
        if self.of_followup_project_id:
            ctx = self._context.copy()
            ctx.update({'search_default_order_id': self.id})
            action['context'] = ctx
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


class File(dms_base.DMSModel):
    _inherit = 'muk_dms.file'

    @api.model
    def of_get_object_partner_and_category(self, obj):
        if obj._name == 'of.followup.project':
            partner = obj.partner_id
            categ = self.env.ref('of_followup.of_followup_project_file_category')
        else:
            partner, categ = super(File, self).of_get_object_partner_and_category(obj)
        return partner, categ

    @api.multi
    def action_view_linked_record(self):
        result = super(File, self).action_view_linked_record()
        if self.of_file_type == 'related' and self.of_related_model == 'of.followup.project':
            result['view_id'] = self.env.ref('of_followup.of_followup_project_form_view').id
        return result
