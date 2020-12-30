# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# 1:  imports of odoo
from odoo import models, fields, api, _


class LabelPrint(models.Model):
    _name = "label.print"

    name = fields.Char("Name", size=64, required=True, index=True)
    model_id = fields.Many2one('ir.model', 'Model', required=True, index=True)
    mode = fields.Selection([
        ('fields', u"Définir les champs"),
        ('template', u"Utiliser un template"),
    ], string=u"Mode de définition", default='template')
    template_id = fields.Many2one(comodel_name="ir.ui.view", help=u"""
    template Qweb définissant l'affichage de l'intérieur de l'étiquette
    ATTENTION: ce template doit avoir un ID externe pour être pris en compte.
        s'il n'en a pas (création à la volée) vous pouvez en générer un en exportant votre template
        le sélectionner en vue liste et faire action > exporter
    """)
    template_id_arch = fields.Text(related="template_id.arch_base", readonly=True)
    template_css_id = fields.Many2one(comodel_name="ir.ui.view", help=u"""
    template Qweb définissant la feuille de style de l'intérieur de l'étiquette
    ATTENTION: ce template doit avoir un ID externe pour être pris en compte.
        s'il n'en a pas (création à la volée) vous pouvez en générer un en exportant votre template
        le sélectionner en vue liste et faire action > exporter
    """)
    template_css_id_arch = fields.Text(related="template_css_id.arch_base", readonly=True)
    field_ids = fields.One2many("label.print.field", 'report_id', string='Fields', copy=True)
    ref_ir_act_report = fields.Many2one('ir.actions.act_window',
                                        'Sidebar action', readonly=True,
                                        help="""Sidebar action to make this
                                        template available on records
                                        of the related document model""")
    ref_ir_value = fields.Many2one('ir.values', 'Sidebar button',
                                   readonly=True,
                                   help="Sidebar button to open the \
                                   sidebar action")
    model_list = fields.Char('Model List', size=256)

    active = fields.Boolean(string=u"Active", default=True)
    label_brand_id = fields.Many2one(comodel_name='label.brand', string='Brand', required=True)
    label_config_id = fields.Many2one(comodel_name='label.config', string='Template', required=True)
    line_field_id = fields.Many2one(
        comodel_name='ir.model.fields', string=u"Champ des lignes",
        domain="[('id', 'in', line_field_domain and line_field_domain[0] and line_field_domain[0][2] or False)]")
    line_field_domain = fields.Many2many(comodel_name='ir.model.fields', compute='_compute_line_field_domain')
    line_field_name = fields.Char(string=u"Nom du champ de lignes", compute="_compute_line_model_id", store=True)
    line_model_id = fields.Many2one(
        comodel_name='ir.model', string=u"Modèle des lignes", compute="_compute_line_model_id", store=True)

    @api.depends('model_id')
    def _compute_line_field_domain(self):
        for record in self:
            field_ids_list = []
            if record.model_id:
                # récupérer les id de tous les champs O2M ou M2M de record.model_id
                fields = self.env['ir.model.fields'].search(
                    [('model', '=', record.model_id.model), ('ttype', 'in', ['one2many', 'many2many'])])
                field_ids_list = fields and fields.ids or []
            record.line_field_domain = field_ids_list

    @api.depends('line_field_id')
    def _compute_line_model_id(self):
        for record in self:
            if record.line_field_id:
                model_name = record.line_field_id.relation
                model_id = self.env['ir.model'].search([('model', '=', model_name)])
                record.line_model_id = model_id and model_id[0] or False
                record.line_field_name = record.line_field_id.name

    @api.onchange('model_id', 'line_field_id')
    def onchange_models_id(self):
        self.ensure_one()
        model_id = self.line_model_id or self.model_id or False
        model_list = []
        if model_id:
            model_obj = self.env['ir.model']
            current_model = model_id.model
            model_list.append(current_model)
            active_model_obj = self.env[model_id.model]
            if active_model_obj._inherits:
                for key, val in active_model_obj._inherits.items():
                    model_ids = model_obj.search([('model', '=', key)])
                    if model_ids:
                        model_list.append(key)
            field_code = []
            for field in self.field_ids:
                if isinstance(field.id, int) and field.field_id.model_id != model_id:
                    field_code.append((2, field.id, 0))
            self.field_ids = field_code
        self.model_list = model_list

    @api.onchange('model_id')
    def onchange_model_id(self):
        u"""Mettre à jour le domain des champs de lignes possibles"""
        field_ids_list = []
        if self.model_id:
            # récupérer les id de tous les champs O2M ou M2M de record.model_id
            fields = self.env['ir.model.fields'].search(
                [('model', '=', self.model_id.model), ('ttype', 'in', ['one2many', 'many2many'])])
            field_ids_list = fields and fields.ids or []
        self.line_field_domain = field_ids_list
        if self.line_field_id and self.line_field_id.id not in field_ids_list:
            self.line_field_id = False
        res = {'domain': {'line_field_id': [('id', 'in', field_ids_list)]}}
        return res

    @api.multi
    def create_action(self):
        vals = {}
        action_obj = self.env['ir.actions.act_window']
        for data in self.browse(self.ids):
            src_obj = data.model_id.model
            button_name = _('Label (%s)') % data.name
            vals['ref_ir_act_report'] = action_obj.create({
                'name': button_name,
                'type': 'ir.actions.act_window',
                'res_model': 'label.print.wizard',
                'src_model': src_obj,
                'view_type': 'form',
                'context': "{'label_print' : %d}" % (data.id),
                'view_mode': 'form,tree',
                'target': 'new',
            })
            id_temp = vals['ref_ir_act_report'].id
            vals['ref_ir_value'] = self.env['ir.values'].create({
                'name': button_name,
                'model': src_obj,
                'key2': 'client_action_multi',
                'value': "ir.actions.act_window," + str(id_temp),
                'object': True,
            })
        self.write({
            'ref_ir_act_report': vals.get('ref_ir_act_report', False).id,
            'ref_ir_value': vals.get('ref_ir_value', False).id,
        })
        return True

    @api.multi
    def unlink_action(self):
        for template in self:
            if template.ref_ir_act_report.id:
                template.ref_ir_act_report.unlink()
            if template.ref_ir_value.id:
                template.ref_ir_value.unlink()
        return True


class LabelPrintField(models.Model):
    _name = "label.print.field"
    _rec_name = "sequence"
    _order = "sequence"

    sequence = fields.Integer("Sequence", required=True)
    name = fields.Char(string=u"Nom", required=True)
    field_id = fields.Many2one('ir.model.fields', 'Fields', required=False)
    report_id = fields.Many2one('label.print', 'Report')
    type = fields.Selection([('normal', 'Normal'), ('barcode', 'Barcode'),
                             ('image', 'Image')],
                            'Type', required=True, default='normal')
    python_expression = fields.Boolean('Python Expression')
    python_field = fields.Char('Fields', size=32)
    fontsize = fields.Float("Font Size", default=12.0)
    position = fields.Selection([('left', 'Left'), ('right', 'Right'),
                                 ('top', 'Top'), ('bottom', 'Bottom')],
                                'Position')
    nolabel = fields.Boolean('No Label')
    newline = fields.Boolean('New Line', default=True)

    css_string = fields.Char(string="CSS string")
    css_value = fields.Char(string="CSS field")
    width = fields.Float(string=u'Largeur (px)', default=50)
    height = fields.Float(string=u'Hauteur (px)', default=50)

    @api.onchange('field_id')
    def _onchange_field_id(self):
        self.ensure_one()
        if self.field_id:
            self.name = self.field_id.name


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=None):
        data = self._context.get('model_list')
        if data:
            args.append(('model', 'in', eval(data)))
        ret_vat = super(IrModelFields, self).name_search(name=name,
                                                         args=args,
                                                         operator=operator,
                                                         limit=limit)
        return ret_vat
