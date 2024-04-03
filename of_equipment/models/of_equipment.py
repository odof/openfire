# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models

from odoo.addons.of_geolocalize.models.res_partner import GEOCODING_STATE, OPENSTREETMAP_PRECISION


class OFEquipment(models.Model):
    _name = 'of.equipment'
    _description = "Equipment"

    active = fields.Boolean(default=True)
    name = fields.Char(string="Serial Number", size=64, copy=False)
    warranty_type = fields.Selection(
        selection=[('in_warranty', 'In warranty'), ('expired', 'Expired'), ('extension', 'Extension')],
        compute='_compute_warranty_type',
        store=True,
        readonly=False,
    )
    state = fields.Selection(
        selection=[
            ('new', "New"),
            ('good', "Good"),
            ('used', "Used"),
            ('to_replace', "To replace"),
        ],
        default='new',
    )
    product_id = fields.Many2one(comodel_name='product.product', string="Product", required=True, ondelete='restrict')
    product_category_id = fields.Many2one(
        comodel_name='product.category',
        string="Category",
        compute='_compute_product_category_id',
        store=True,
        readonly=False,
    )
    brand_id = fields.Many2one(
        comodel_name='of.product.brand', string="Brand", compute='_compute_brand_id', store=True, readonly=False
    )
    model_name = fields.Char()
    installation_type = fields.Char()
    is_compliant = fields.Boolean(string="Compliant", default=True)
    piece_number = fields.Char(size=64, required=False)
    note = fields.Text()
    lot_id = fields.Many2one(comodel_name='stock.lot', string="Origin Lot")
    operator_id = fields.Many2one(comodel_name='hr.employee', string="Operator")

    # Dates
    service_date = fields.Date()
    installation_date = fields.Date()
    end_warranty_date = fields.Date(string="End of Warranty")

    # Customer and site
    customer_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer",
        required=True,
        domain="[('parent_id', '=', False)]",
        ondelete='restrict',
    )
    site_address_id = fields.Many2one(
        comodel_name='res.partner',
        string="Installation Site",
        required=False,
        domain="['|', ('parent_id', '=', customer_id), ('id', '=', customer_id)]",
        ondelete='restrict',
        compute='_compute_site_address_id',
        store=True,
        readonly=False,
    )
    site_phone_number_ids = fields.One2many(related='site_address_id.of_phone_number_ids')
    site_street = fields.Char(string="Street", related='site_address_id.street')
    site_street2 = fields.Char(string="Street 2", related='site_address_id.street2')
    site_zip = fields.Char(string="Zip", related='site_address_id.zip', store=True)
    site_city = fields.Char(string="City", related='site_address_id.city')
    site_country_id = fields.Many2one(
        comodel_name='res.country', string="Country", related='site_address_id.country_id'
    )

    # Reseller and installer
    reseller_id = fields.Many2one(comodel_name='res.partner', string="Reseller", ondelete='restrict')
    installer_id = fields.Many2one(comodel_name='res.partner', string="Installer", ondelete='restrict')
    installer_address_id = fields.Many2one(
        comodel_name='res.partner',
        string="Installer Address",
        domain="['|', ('parent_id', '=', installer_id), ('id', '=', installer_id)]",
        ondelete='restrict',
    )

    # Interventions
    intervention_ids = fields.Many2many(
        comodel_name='calendar.event',
        relation='of_calendar_event_equipment_rel',
        column1='equipment_id',
        column2='intervention_id',
        string="Interventions",
    )

    # Order
    order_ids = fields.Many2many(comodel_name='sale.order', string="Orders")
    orders_count = fields.Integer(string="Orders count", compute='_compute_orders_count')

    # Invoice
    invoice_ids = fields.Many2many(comodel_name='account.move', string="Invoices")
    invoices_count = fields.Integer(string="Invoices count", compute='_compute_invoices_count')

    # Map view fields
    customer_name = fields.Char(related='customer_id.name')
    customer_mobile = fields.Char(related='customer_id.mobile')
    precision = fields.Selection(
        OPENSTREETMAP_PRECISION, compute='_compute_geocoding_data', string="Precision", store=True
    )
    partner_latitude = fields.Float(string="Latitude", compute='_compute_geocoding_data', store=True)
    partner_longitude = fields.Float(string="Longitude", compute='_compute_geocoding_data', store=True)
    geocoding_state = fields.Selection(
        GEOCODING_STATE,
        default='not_tried',
        help="State of geocoding",
        compute='_compute_geocoding_data',
        store=True,
    )

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends('end_warranty_date')
    def _compute_warranty_type(self):
        for equipment in self:
            if equipment.end_warranty_date:
                if equipment.end_warranty_date < fields.Date.today():
                    equipment.warranty_type = 'expired'
                elif equipment.end_warranty_date >= fields.Date.today() and equipment.warranty_type == 'expired':
                    equipment.warranty_type = 'extension'
                else:
                    equipment.warranty_type = 'in_warranty'

    @api.depends('product_id')
    def _compute_product_category_id(self):
        for equipment in self:
            if equipment.product_id:
                equipment.product_category_id = equipment.product_id.categ_id

    @api.depends('product_id')
    def _compute_brand_id(self):
        for equipment in self:
            if equipment.product_id:
                equipment.brand_id = equipment.product_id.brand_id

    @api.depends('customer_id')
    def _compute_site_address_id(self):
        for equipment in self:
            if equipment.customer_id:
                equipment.site_address_id = equipment.customer_id

    @api.depends('order_ids')
    def _compute_orders_count(self):
        for equipment in self:
            equipment.orders_count = len(equipment.order_ids)

    @api.depends('invoice_ids')
    def _compute_invoices_count(self):
        for equipment in self:
            equipment.invoices_count = len(equipment.invoice_ids)

    @api.depends(
        'customer_id',
        'customer_id.of_precision',
        'customer_id.partner_latitude',
        'customer_id.partner_longitude',
        'customer_id.of_geocoding_state',
        'site_address_id',
        'site_address_id.of_precision',
        'site_address_id.partner_latitude',
        'site_address_id.partner_longitude',
        'site_address_id.of_geocoding_state',
    )
    def _compute_geocoding_data(self):
        for equipment in self:
            if equipment.site_address_id:
                equipment.precision = equipment.site_address_id.of_precision
                equipment.partner_latitude = equipment.site_address_id.partner_latitude
                equipment.partner_longitude = equipment.site_address_id.partner_longitude
                equipment.geocoding_state = equipment.site_address_id.of_geocoding_state
            else:
                equipment.precision = equipment.customer_id.of_precision
                equipment.partner_latitude = equipment.customer_id.partner_latitude
                equipment.partner_longitude = equipment.customer_id.partner_longitude
                equipment.geocoding_state = equipment.customer_id.of_geocoding_state

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        equipments = super().create(vals_list)
        resellers_equipments = equipments.filtered(lambda e: e.reseller_id and not e.reseller_id.of_is_reseller)
        resellers_equipments.mapped('reseller_id').write({'of_is_reseller': True})
        installers_equipments = equipments.filtered(lambda e: e.installer_id and not e.installer_id.of_is_installer)
        installers_equipments.mapped('installer_id').write({'of_is_installer': True})
        return equipments

    def write(self, vals):
        res = super().write(vals)
        if vals.get('reseller_id'):
            non_reseller_partners = self.mapped('reseller_id').filtered(lambda p: not p.of_is_reseller)
            non_reseller_partners.write({'of_is_reseller': True})
        if vals.get('installer_id'):
            non_installer_partners = self.mapped('installer_id').filtered(lambda p: not p.of_is_installer)
            non_installer_partners.write({'of_is_installer': True})
        return res

    def name_get(self):
        """
        Return the name of the equipment.

        If the context is 'equipment_simple_name_display', return the standard name.
        Otherwise, return a formatted name based on the customer ID, equipment name, product name, and
        customer display name.
        If customer_id is in the context and its the same as the equipment's customer_id, add a prefix "-> ".

        :return: A list of tuples containing the equipment ID and its name.
        :rtype: list
        """
        if self._context.get('equipment_simple_name_display'):
            return super().name_get()

        customer_id = self._context.get('partner_id_serial_number')
        customer_id = customer_id and int(customer_id) or False
        result = []
        for record in self:
            if customer_id:
                prefix = "-> " if record.customer_id.id == customer_id else ""
                name = f"{prefix}{record.name or '(No. not specified)'} - {record.customer_id.display_name}"
            else:
                name = (
                    f"{f'{record.name} ' if record.name else ''}"
                    f"{record.product_id.name} - {record.customer_id.display_name}"
                )
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Permet dans un SAV lors de la saisie du no de série d'une machine installée de proposer les machines
        du contact en premier précédées d'une puce.
        Permet, dans une DI, de montrer en 1er les appareils de l'adresse, puis ceux du customer et enfin les autres.
        """
        if customer_id := self._context.get('partner_id_serial_number'):
            customer_equipments = super().name_search(name, [('customer_id', '=', customer_id)], operator, limit) or []
            limit = limit - len(customer_equipments)
            customer_equipments = [(equipment[0], f"-> {equipment[1]}") for equipment in customer_equipments]
            return (  # customer equipments, other equipments
                customer_equipments + super().name_search(name, [('customer_id', '!=', customer_id)], operator, limit)
                or []
            )
        if address_id := self._context.get('address_prio_id'):
            args = args or []
            address_equipments = (
                super().name_search(name, args + [['site_address_id', '=', address_id]], operator, limit) or []
            )
            limit = limit - len(address_equipments)
            address_customer_equipments = address_equipments + (
                super().name_search(
                    name,
                    args
                    + [
                        '|',
                        ['site_address_id', '=', False],
                        ['site_address_id', '!=', address_id],
                        ['customer_id', '=', address_id],
                    ],
                    operator,
                    limit,
                )
                or []
            )
            limit = limit - len(address_customer_equipments)
            return address_customer_equipments + (  # address equipments, customer equipments and other equipments
                super().name_search(
                    name,
                    args
                    + [
                        '|',
                        ['site_address_id', '=', False],
                        ['site_address_id', '!=', address_id],
                        ['customer_id', '!=', address_id],
                    ],
                    operator,
                    limit,
                )
                or []
            )
        return super().name_search(name, args, operator, limit)

    # --------------------------------------------------------------------------
    # Action methods
    # --------------------------------------------------------------------------

    def action_button_view_order(self):
        orders = self.mapped('order_ids')
        action = self.env.ref('sale.action_orders').read()[0]
        action['context'] = {
            'default_of_use_equipment': True,
            'default_of_equipment_ids': [Command.set(self.ids)],
            'default_partner_id': len(self) == 1 and self.customer_id.id or False,
        }
        if len(orders) > 1:
            action['domain'] = [('id', 'in', orders.ids)]
        elif len(orders) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = orders.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_button_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    @api.model
    def cron_recompute_warranty_type_daily(self):
        """
        Recomputes the warranty type daily for equipment.

        This method updates the warranty type of equipment based on their end warranty date.
        It sets the warranty type to 'initial' for equipment with a future end warranty date,
        and sets the warranty type to 'expired' for equipment with a past end warranty date.
        """
        today = fields.Date.today()
        all_equipments_with_warranty = self.search([('end_warranty_date', '!=', False)])
        equipments_without_warranty_type = all_equipments_with_warranty.filtered(
            lambda p: p.end_warranty_date >= today and not p.warranty_type
        )
        equipments_without_warranty_type.write({'warranty_type': 'in_warranty'})
        equipments_with_expired_warranty = all_equipments_with_warranty.filtered(
            lambda p: p.end_warranty_date < today and p.warranty_type != 'expired'
        )
        equipments_with_expired_warranty.write({'warranty_type': 'expired'})
