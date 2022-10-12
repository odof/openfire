# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from operator import add
from odoo import models, fields, api


class OFSaleWizardSetPrintingParams(models.TransientModel):
    _name = 'of.sale.wizard.set.printing.params'

    def _get_dict_fields_mapping(self):
        """ Returns a dict of the fields to migrate or to add.
        """
        return {
            'pdf_address_title': {'default_value': True, 'oldname': 'pdf_hide_global_address_label'},
            'pdf_address_contact_titles': {'default_value': False, 'oldname': 'pdf_adresse_civilite'},
            'pdf_address_contact_parent_name': {'default_value': False, 'oldname': 'pdf_adresse_nom_parent'},
            'pdf_address_contact_name': {'default_value': True, 'oldname': False},
            'pdf_address_contact_phone': {
                'default_value': True, 'oldname': 'pdf_adresse_telephone', 'linked_to': 'pdf_customer_phone'},
            'pdf_address_contact_mobile': {
                'default_value': True, 'oldname': 'pdf_adresse_mobile', 'linked_to': 'pdf_customer_mobile'},
            'pdf_address_contact_fax': {
                'default_value': False, 'oldname': 'pdf_adresse_fax', 'linked_to': 'pdf_customer_fax'},
            'pdf_address_contact_email': {
                'default_value': True, 'oldname': 'pdf_adresse_email', 'linked_to': 'pdf_customer_email'},
            'pdf_commercial_insert': {'default_value': True, 'oldname': 'pdf_masquer_pastille_commercial'},
            'pdf_commercial_contact': {'default_value': True, 'oldname': False},
            'pdf_commercial_email': {'default_value': False, 'oldname': 'pdf_mail_commercial'},
            'pdf_customer_insert': {'default_value': True, 'oldname': False},
            'pdf_customer_phone': {'default_value': True, 'oldname': False},
            'pdf_customer_mobile': {'default_value': True, 'oldname': False},
            'pdf_customer_fax': {'default_value': True, 'oldname': False},
            'pdf_customer_email': {'default_value': True, 'oldname': False},
            'pdf_payment_term_insert': {'default_value': True, 'oldname': 'pdf_masquer_pastille_payment_term'},
            'pdf_technical_visit_insert': {'default_value': False, 'oldname': 'pdf_vt_pastille'},
            'pdf_validity_insert': {'default_value': False, 'oldname': 'pdf_date_validite_devis'},
            'pdf_section_bg_color': {'default_value': '#FFFFFF', 'oldname': 'of_color_bg_section'},
            'pdf_section_font_color': {'default_value': '#000000', 'oldname': 'of_color_font'},
            'pdf_product_reference': {'default_value': False, 'oldname': 'pdf_display_product_ref_setting'},
            'pdf_payment_schedule': {'default_value': False, 'oldname': 'pdf_afficher_multi_echeances'},
            'pdf_taxes_detail': {'default_value': False, 'oldname': 'of_pdf_taxes_display'},
        }

    def _get_ir_values_settings_value(self, contact_selection_fields, reverted_fields, name, oldname, current_values):
        if name in contact_selection_fields:
            # special case for contact selection fields
            return current_values.get(oldname) % 2 == 1
        elif oldname in reverted_fields:
            # some fields have been reverted : "hide" -> "show"
            return not current_values.get(oldname)
        else:
            return current_values.get(oldname)

    @api.model
    def _auto_init(self):
        """ Version 10.0.3.0.0 : new version of PDf printing settings (fields and data migration).
        """
        IrValues = self.env['ir.values']

        should_be_updated = IrValues.get_default('sale.config.settings', 'pdf_settings_target_version') != '10.0.3.0.0'

        current_module = self.env['ir.module.module'].search([('name', '=', 'of_sale')])
        latest_version = current_module.latest_version
        if latest_version < '10.0.3.0.0' and should_be_updated:
            # list of fields that were changed from selection to boolean
            contact_selection_fields = [
                'pdf_address_contact_phone', 'pdf_address_contact_mobile', 'pdf_address_contact_fax',
                'pdf_address_contact_email']
            # list of fields whose values were reverted (a negative setting become positive)
            reverted_fields = [
                'pdf_hide_global_address_label', 'pdf_masquer_pastille_commercial',
                'pdf_masquer_pastille_payment_term']
            # dict of new fields names and the oldnames and their default values
            mapping_data_dict = self._get_dict_fields_mapping()
            # we will delete the old fields
            to_unlink = [data['oldname'] for data in mapping_data_dict.values() if data['oldname']]
            # save the current values of the old fields to update the new fields
            current_values = {
                current_name: IrValues.get_default('sale.config.settings', current_name) for current_name in to_unlink}

            for field in contact_selection_fields:
                # if this field was not set to be displayed in an additional customer insert or in both insert
                # (current value == 1 or never set) then we set the default value to False for the new field.
                # that's because we don't want to activate unwanted fields (keep the previous display behavior)
                oldname = mapping_data_dict[field]['oldname']
                if current_values.get(oldname) in [1, False, None]:
                    linked_to = mapping_data_dict[field]['linked_to']
                    # update the default value of the linked field
                    mapping_data_dict[linked_to]['default_value'] = False

        res = super(OFSaleWizardSetPrintingParams, self)._auto_init()

        if latest_version < '10.0.3.0.0' and should_be_updated:
            # create new settings or update existing ones
            for name, data in mapping_data_dict.items():
                if data['oldname'] and data['oldname'] in current_values:
                    if IrValues.get_default('sale.config.settings', data['oldname']) is not None:
                        # get the correct value for the new field
                        value = self._get_ir_values_settings_value(
                            contact_selection_fields, reverted_fields, name, data['oldname'], current_values)
                    elif IrValues.get_default('sale.config.settings', data['oldname']) is None:
                        # case where the old field was not set example of "pdf_masquer_pastille_commercial" can has
                        # never been set to True
                        value = data['default_value']
                    IrValues.set_default('sale.config.settings', name, value)
                elif not data['oldname'] and IrValues.get_default('sale.config.settings', name) is None:
                    IrValues.set_default('sale.config.settings', name, data['default_value'])
            # delete old settings
            IrValues.search([('model', '=', 'sale.config.settings'), ('name', 'in', to_unlink)]).unlink()
            # set the target version to avoid calling this function again
            IrValues.set_default('sale.config.settings', 'pdf_settings_target_version', '10.0.3.0.0')
        return res

    # Address insert
    pdf_address_title = fields.Boolean(
        string="Address title", default=True,
        help="If checked, displays the label \"Delivery and billing address\"")
    pdf_address_contact_titles = fields.Boolean(
        string="Titles", default=False, help="If checked, displays the titles in the address insert")
    pdf_address_contact_parent_name = fields.Boolean(
        string="Contact's parent name", default=False,
        help="If checked, displays the contact's parent name in the address insert")
    pdf_address_contact_name = fields.Boolean(
        string="Contact's name", default=True,
        help="If checked, displays the contact's name in the address insert")
    pdf_address_contact_phone = fields.Boolean(
        string="Phone", default=True,
        help="If checked, displays the contact's phone in the address insert")
    pdf_address_contact_mobile = fields.Boolean(
        string="Mobile", default=True,
        help="If checked, displays the contact's mobile in the address insert")
    pdf_address_contact_fax = fields.Boolean(
        string="Fax", default=False,
        help="If checked, displays the contact's fax in the address insert")
    pdf_address_contact_email = fields.Boolean(
        string="Email", default=True,
        help="If checked, displays the contact's mail in the address insert")

    # Commercial insert
    pdf_commercial_insert = fields.Boolean(
        string="Commercial insert", default=False, help="If checked, displays the commercial insert")
    pdf_commercial_contact = fields.Boolean(
        string="Contact", default=True, help="If checked, displays the contact in the commercial insert")
    pdf_commercial_email = fields.Boolean(
        string="Email", default=False, help="If checked, displays the email in the commercial insert")

    # Customers insert
    pdf_customer_insert = fields.Boolean(
        string="Customers insert", default=True, help="If checked, displays the customers insert")
    pdf_customer_phone = fields.Boolean(
        string="Phone", default=True, help="If checked, displays the customer's phone in the customers insert")
    pdf_customer_mobile = fields.Boolean(
        string="Mobile", default=True, help="If checked, displays the customer's mobile in the customers insert")
    pdf_customer_fax = fields.Boolean(
        string="Fax", default=True, help="If checked, displays the customer's fax in the customers insert")
    pdf_customer_email = fields.Boolean(
        string="Email", default=True, help="If checked, displays the customer's email in the customers insert")

    # Inserts
    pdf_payment_term_insert = fields.Boolean(
        string="Payment terms", default=True, help="If checked, displays the payment terms in the inserts")
    pdf_technical_visit_insert = fields.Boolean(
        string="Date of technical visit", default=False,
        help="If checked, displays the technical visit date in the inserts")
    pdf_validity_insert = fields.Boolean(
        string="Validity date", default=False,
        help="If checked, displays the validity date in the inserts")
    group_display_incoterm = fields.Boolean(
        string="Incoterms",
        implied_group='sale.group_display_incoterm',
        help="If checked, the printed reports will display the incoterms for the sales orders and the related invoices")

    # Sections
    pdf_section_bg_color = fields.Char(
        string="Background color", default="#FFFFFF",
        help="Background color of the section headings. Default is white.")
    pdf_section_font_color = fields.Char(
        string="Font color", default="#000000",
        help="Font color of the section headings. Default is black.")

    # Order lines
    pdf_product_reference = fields.Boolean(
        string="Product reference", default=False,
        help="If checked, displays the product reference in the order lines on the report")

    # Other
    pdf_payment_schedule = fields.Boolean(
        string="Payment schedule", default=False,
        help="If checked, displays the Payment schedule in the report")
    pdf_taxes_detail = fields.Boolean(
        string="Taxes detail", default=False, help="If checked, displays the taxes detail in the report")

    @api.onchange('pdf_commercial_insert')
    def onchange_pdf_commercial_insert(self):
        # we have to check the value of the field before the onchange is applied, because when the form is loaded, the
        # onchange will update the value of the field even if it is not changed by the user
        origin_value = self.env['ir.values'].get_default('sale.config.settings', 'pdf_commercial_insert')
        if not origin_value and self.pdf_commercial_insert and not self.pdf_commercial_contact:
            self.pdf_commercial_contact = True
        if not origin_value and self.pdf_commercial_insert and not self.pdf_commercial_email:
            self.pdf_commercial_email = True

    @api.model
    def _get_groups_fields(self):
        ref = self.env.ref
        groups = []
        for name, field in self._fields.iteritems():
            if name.startswith('group_') and field.type in ('boolean', 'selection') and \
                    hasattr(field, 'implied_group'):
                field_group_xmlids = getattr(field, 'group', 'base.group_user').split(',')
                field_groups = reduce(add, map(ref, field_group_xmlids))
                groups.append((name, field_groups, ref(field.implied_group)))
        return groups

    @api.model
    def default_get(self, fields_list):

        res = super(OFSaleWizardSetPrintingParams, self).default_get(fields_list)

        IrValues = self.env['ir.values']

        # groups: which groups are implied by the group Employee
        for name, groups, implied_group in self._get_groups_fields():
            res[name] = all(implied_group in group.implied_ids for group in groups)
            if self._fields[name].type == 'selection':
                res[name] = int(res[name])

        defaults = {}
        ir_values_dict = IrValues.get_defaults_dict('sale.config.settings')
        for name in fields_list:
            if name in ir_values_dict:
                defaults[name] = ir_values_dict[name]
                continue
        defaults = self._convert_to_write(defaults)
        res.update(defaults)
        return res

    @api.multi
    def set_pdf_address_title(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_address_title', self.pdf_address_title)

    @api.multi
    def set_pdf_address_contact_titles(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_address_contact_titles', self.pdf_address_contact_titles)

    @api.multi
    def set_pdf_address_contact_parent_name(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_address_contact_parent_name', self.pdf_address_contact_parent_name)

    @api.multi
    def set_pdf_address_contact_name(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_address_contact_name', self.pdf_address_contact_name)

    @api.multi
    def set_pdf_address_contact_phone(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_address_contact_phone', self.pdf_address_contact_phone)

    @api.multi
    def set_pdf_address_contact_mobile(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_address_contact_mobile', self.pdf_address_contact_mobile)

    @api.multi
    def set_pdf_address_contact_fax(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_address_contact_fax', self.pdf_address_contact_fax)

    @api.multi
    def set_pdf_address_contact_email(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_address_contact_email', self.pdf_address_contact_email)

    @api.multi
    def set_pdf_commercial_insert(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_commercial_insert', self.pdf_commercial_insert)

    @api.multi
    def set_pdf_commercial_contact(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_commercial_contact', self.pdf_commercial_contact)

    @api.multi
    def set_pdf_commercial_email(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_commercial_email', self.pdf_commercial_email)

    @api.multi
    def set_pdf_customer_insert(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_customer_insert', self.pdf_customer_insert)

    @api.multi
    def set_pdf_customer_phone(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_customer_phone', self.pdf_customer_phone)

    @api.multi
    def set_pdf_customer_mobile(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_customer_mobile', self.pdf_customer_mobile)

    @api.multi
    def set_pdf_customer_fax(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_customer_fax', self.pdf_customer_fax)

    @api.multi
    def set_pdf_customer_email(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_customer_email', self.pdf_customer_email)

    @api.multi
    def set_pdf_payment_term_insert(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_payment_term_insert', self.pdf_payment_term_insert)

    @api.multi
    def set_pdf_technical_visit_insert(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_technical_visit_insert', self.pdf_technical_visit_insert)

    @api.multi
    def set_pdf_validity_insert(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_validity_insert', self.pdf_validity_insert)

    @api.multi
    def set_pdf_section_bg_color(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_section_bg_color', self.pdf_section_bg_color)

    @api.multi
    def set_pdf_section_font_color(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_section_font_color', self.pdf_section_font_color)

    @api.multi
    def set_pdf_product_reference(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_product_reference', self.pdf_product_reference)

    @api.multi
    def set_pdf_payment_schedule(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_payment_schedule', self.pdf_payment_schedule)

    @api.multi
    def set_pdf_taxes_detail(self):
        return self.env['ir.values'].sudo().set_default(
            'sale.config.settings', 'pdf_taxes_detail', self.pdf_taxes_detail)

    @api.multi
    def action_validate(self):

        # Get the default values of the groups and check if the value has been changed
        groups_fields = [field_name for field_name in self.fields_get().keys() if field_name.startswith('group_')]
        printingsettings_groups_cache = {
            field_name: default_value
            for field_name, default_value in self.default_get(self.fields_get().keys()).iteritems()
            if field_name.startswith('group_')}
        printingsettings_groups_has_changed = [
            field_name
            for field_name in groups_fields
            if getattr(self, field_name) != printingsettings_groups_cache[field_name]]

        # Call the set methods
        for method in dir(self):
            if method.startswith('set_'):
                getattr(self, method)()

        if printingsettings_groups_has_changed:
            # filter groups to recompute only modified ones
            only_changed_values = filter(
                lambda gval: gval and gval[0] in printingsettings_groups_has_changed, self._get_groups_fields())
            if only_changed_values:
                with self.env.norecompute():
                    for name, groups, implied_group in only_changed_values:
                        if self[name]:
                            groups.write({'implied_ids': [(4, implied_group.id)]})
                        else:
                            groups.write({'implied_ids': [(3, implied_group.id)]})
                            implied_group.write({'users': [(3, user.id) for user in groups.mapped('users')]})
                self.recompute()
