from odoo import api, fields, models, SUPERUSER_ID


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    @api.multi
    def name_get(self):
        res = []
        for field in self:
            res.append((field.id, '%s' % (field.field_description,)))
        return res


class ListEditor(models.Model):
    _name = 'list.editor'

    full_key = fields.Char(index=True)
    model_id = fields.Many2one('ir.model', string='Model')
    visible_fields = fields.Many2many('ir.model.fields', string='Fields', domain="[('model_id', '=', model_id)]")
    default_visible_columns = fields.Char(default='')
    fields_sequence = fields.Char(default='')
    editable = fields.Selection([('top', 'Top'), ('bottom', 'Bottom')], string='Editable')

    def get_list_editor_form_id(self):
        return self.env.ref('list_editor.list_editor_form').id

    @api.model
    def open_list_editor(self, key=None):
        view = self.search([('full_key', '=', key + str(self._uid))])

        if len(view) <= 0:
            return {
                'open_for_create': True,
                'view_id': self.get_list_editor_form_id()
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'List Editor',
                'res_model': 'list.editor',
                'views': [[self.get_list_editor_form_id(), 'form']],
                'view_type': "form",
                'view_mode': "form",
                'target': 'new',
                'res_id': view[0].id
            }

    @api.model
    def get_visible_fields_ids(self, model, visible_fields):
        model = self.env['ir.model'].search([('model', '=', model)])
        if len(model) <= 0:
            return False

        model = model[0]
        visible = self.env['ir.model.fields'].search([('model_id', '=', model.id), ('name', 'in', visible_fields)])
        visible = visible.sorted(lambda x: visible_fields.index(x.name))
        return {
            'model_id': model.id,
            'visible_ids': visible.ids,
        }

    @api.onchange('visible_fields')
    def _compute_fields_sequence(self):
        self.fields_sequence = ','.join([str(x) for x in self.visible_fields.ids])

    @api.multi
    def create_or_edit(self):
        self.ensure_one()

        view = self.env['list.editor'].search([('full_key', '=', self.full_key)])

        if len(view) >= 1:
            view[0].write({})

    @api.multi
    def restore(self):
        self.ensure_one()
        self.unlink()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def get_list_view(self, key):
        view = self.search([('full_key', '=', key + str(self._uid))])
        if len(view) <= 0:
            view = self.search([('full_key', '=', key + str(SUPERUSER_ID))])
        if len(view) <= 0:
            return False

        view = view[0]
        fields_sequence_ids = [int(x) for x in view.fields_sequence.split(',')]
        visible_columns = self.env['ir.model.fields'].browse(fields_sequence_ids)

        new_fields = visible_columns.filtered(lambda x: x.state == 'manual').mapped('name')

        return {
            'editable': view.editable,
            'new_fields': self.env[view.model_id.model].fields_get(new_fields) if len(new_fields) > 0 else {},
            'visible_columns': visible_columns.mapped('name'),
        }

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        res = super(ListEditor, self).read(fields, load)
        for record in res:
            visible_fields = record.get('visible_fields')
            if visible_fields:
                fields_sequence = [int(x) for x in record.get('fields_sequence').split(',')]
                visible_fields.sort(key=lambda field: fields_sequence.index(field))
                record['visible_fields'] = visible_fields
        return res
