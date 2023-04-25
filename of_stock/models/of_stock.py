# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools import float_utils
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_inventory import Inventory
from odoo.addons.stock.models.stock_quant import Quant
from odoo.addons.stock.models.stock_move import StockMove
import odoo.addons.decimal_precision as dp

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta


@api.multi
def _get_inventory_lines_values(self):
    # TDE CLEANME: is sql really necessary ? I don't think so
    locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
    domain = ' location_id in %s'
    args = (tuple(locations.ids),)

    vals = []
    Product = self.env['product.product']
    # Empty recordset of products available in stock_quants
    quant_products = self.env['product.product']
    # Empty recordset of products to filter
    products_to_filter = self.env['product.product']
    categ_obj = self.env['product.category']

    # case 0: Filter on company
    if self.company_id:
        domain += ' AND company_id = %s'
        args += (self.company_id.id,)

    # case 1: Filter on One owner only or One product for a specific owner
    if self.partner_id:
        domain += ' AND owner_id = %s'
        args += (self.partner_id.id,)
    # case 2: Filter on One Lot/Serial Number
    if self.lot_id:
        domain += ' AND lot_id = %s'
        args += (self.lot_id.id,)
    # case 3: Filter on One product
    if self.product_id:
        domain += ' AND product_id = %s'
        args += (self.product_id.id,)
        products_to_filter |= self.product_id
    # case 4: Filter on A Pack
    if self.package_id:
        domain += ' AND package_id = %s'
        args += (self.package_id.id,)
    # case 5: Filter on One product category + Exahausted Products
    if self.category_id:
        categ_ids = categ_obj.search([('id', 'child_of', self.category_id.id)])
        categ_products = Product.search([('categ_id', 'in', categ_ids.ids)])
        domain += ' AND product_id = ANY (%s)'
        args += (categ_products.ids,)
        products_to_filter |= categ_products
    # OF case 6 : Filter on multiple product categories/brands
    if self.of_category_ids or self.of_brand_ids:
        product_domain = []
        if self.of_category_ids:
            product_domain += [('categ_id', 'in', self.of_category_ids._ids)]
        if self.of_brand_ids:
            product_domain += [('brand_id', 'in', self.of_brand_ids._ids)]
        categ_products = Product.search(product_domain)
        domain += ' AND product_id = ANY (%s)'
        args += (categ_products.ids,)
        products_to_filter |= categ_products
    if hasattr(self, 'of_option') and self.of_option:
        domain += ' AND in_date <= %s'
        args += (self.date, )
    if hasattr(self, 'of_quant_state') and self.of_quant_state == 'unreserved':
        domain += ' AND reservation_id IS NULL'

    self.env.cr.execute("""SELECT product_id, sum(qty) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
                FROM stock_quant
                WHERE %s
                GROUP BY product_id, location_id, lot_id, package_id, partner_id """ % domain, args)

    for product_data in self.env.cr.dictfetchall():
        # replace the None the dictionary by False, because falsy values are tested later on
        for void_field in [item[0] for item in product_data.items() if item[1] is None]:
            product_data[void_field] = False
        product_data['theoretical_qty'] = product_data['product_qty']
        if product_data['product_id']:
            product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
            quant_products |= Product.browse(product_data['product_id'])
        vals.append(product_data)
    if self.exhausted:
        exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
        vals.extend(exhausted_vals)
    return vals


@api.multi
def action_start(self):
    for inventory in self:
        vals = {'state': 'confirm'}
        if not self.of_option or not self.date:
            vals['date'] = fields.Datetime.now()
        if (inventory.filter != 'partial') and not inventory.line_ids:
            vals.update(
                {'line_ids': [(0, 0, line_values) for line_values in inventory._get_inventory_lines_values()]})
        inventory.write(vals)
    return True


Inventory._get_inventory_lines_values = _get_inventory_lines_values
Inventory.prepare_inventory = action_start


@api.model
def _quant_create_from_move(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                            force_location_from=False, force_location_to=False):
    """Create a quant in the destination location and create a negative
    quant in the source location if it's an internal location. """
    inventory_date = self._context.get('inventory_date', False)
    force_date = self._context.get('force_date_done', False)
    if inventory_date:
        in_date = move.date
    elif force_date:
        in_date = force_date
    else:
        in_date = fields.Datetime.now()
    price_unit = move.get_price_unit()
    location = force_location_to or move.location_dest_id
    rounding = move.product_id.uom_id.rounding
    vals = {
        'product_id': move.product_id.id,
        'location_id': location.id,
        'qty': float_round(qty, precision_rounding=rounding),
        'cost': price_unit,
        'history_ids': [(4, move.id)],
        'in_date': in_date,
        'company_id': move.company_id.id,
        'lot_id': lot_id,
        'owner_id': owner_id,
        'package_id': dest_package_id,
    }
    if move.location_id.usage == 'internal':
        # if we were trying to move something from an internal location and reach here (quant creation),
        # it means that a negative quant has to be created as well.
        negative_vals = vals.copy()
        negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
        negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
        negative_vals['cost'] = price_unit
        negative_vals['negative_move_id'] = move.id
        negative_vals['package_id'] = src_package_id
        negative_quant_id = self.sudo().create(negative_vals)
        vals.update({'propagated_from_id': negative_quant_id.id})

    picking_type = move.picking_id and move.picking_id.picking_type_id or False
    if lot_id and move.product_id.tracking == 'serial' \
            and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
        if qty != 1.0:
            raise UserError(_('You should only receive by the piece with the same serial number'))

    # create the quant as superuser, because we want to restrict the creation
    # of quant manually: we should always use this method to create quants
    return self.sudo().create(vals)


Quant._quant_create_from_move = _quant_create_from_move


@api.multi
def action_done(self):
    """ Process completely the moves given and if all moves are done, it will finish the picking. """
    self.filtered(lambda move: move.state == 'draft').action_confirm()

    Uom = self.env['product.uom']
    Quant = self.env['stock.quant']

    pickings = self.env['stock.picking']
    procurements = self.env['procurement.order']
    operations = self.env['stock.pack.operation']

    remaining_move_qty = {}
    force_date_done = self._context.get('force_date_done', False)

    for move in self:
        if move.picking_id:
            pickings |= move.picking_id
        remaining_move_qty[move.id] = move.product_qty
        for link in move.linked_move_operation_ids:
            operations |= link.operation_id
            pickings |= link.operation_id.picking_id

    # Sort operations according to entire packages first, then package + lot, package only, lot only
    operations = operations.sorted(
        key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (
                    x.pack_lot_ids and -1 or 0))

    for operation in operations:

        # product given: result put immediately in the result package (if False: without package)
        # but if pack moved entirely, quants should not be written anything for the destination package
        quant_dest_package_id = operation.product_id and operation.result_package_id.id or False
        entire_pack = not operation.product_id and True or False

        # compute quantities for each lot + check quantities match
        lot_quantities = dict(
            (pack_lot.lot_id.id, operation.product_uom_id._compute_quantity(pack_lot.qty, operation.product_id.uom_id)
             ) for pack_lot in operation.pack_lot_ids)

        qty = operation.product_qty
        if operation.product_uom_id and operation.product_uom_id != operation.product_id.uom_id:
            qty = operation.product_uom_id._compute_quantity(qty, operation.product_id.uom_id)
        if operation.pack_lot_ids and float_compare(sum(lot_quantities.values()), qty,
                                                    precision_rounding=operation.product_id.uom_id.rounding) != 0.0:
            raise UserError(_('You have a difference between the quantity on the operation '
                              'and the quantities specified for the lots. '))

        quants_taken = []
        false_quants = []
        lot_move_qty = {}

        prout_move_qty = {}
        for link in operation.linked_move_operation_ids:
            prout_move_qty[link.move_id] = prout_move_qty.get(link.move_id, 0.0) + link.qty

        # Process every move only once for every pack operation
        for move in prout_move_qty.keys():
            # TDE FIXME: do in batch ?
            move.check_tracking(operation)

            # TDE FIXME: I bet the message error is wrong
            # Le move n'a pas de quantité restante
            if not remaining_move_qty.get(move.id):
                raise UserError(_(
                    "The roundings of your unit of measure %s on the move vs. %s on the product don't allow to do "
                    "these operations or you are not transferring the picking at once. ") % (
                                move.product_uom.name, move.product_id.uom_id.name))

            if not operation.pack_lot_ids:
                preferred_domain_list = [[('reservation_id', '=', move.id)], [('reservation_id', '=', False)],
                                         ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]]
                quants = Quant.quants_get_preferred_domain(
                    prout_move_qty[move], move, ops=operation, domain=[('qty', '>', 0)],
                    preferred_domain_list=preferred_domain_list)
                # déplace les quants dans l'emplacement de destination
                # si on force la date, seules les quants antérieures sont déplacées
                Quant.quants_move(quants, move, operation.location_dest_id, location_from=operation.location_id,
                                  lot_id=False, owner_id=operation.owner_id.id, src_package_id=operation.package_id.id,
                                  dest_package_id=quant_dest_package_id, entire_pack=entire_pack)
            else:
                # Check what you can do with reserved quants already
                qty_on_link = prout_move_qty[move]
                rounding = operation.product_id.uom_id.rounding
                for reserved_quant in move.reserved_quant_ids:
                    if (reserved_quant.owner_id.id != operation.owner_id.id) or (
                            reserved_quant.location_id.id != operation.location_id.id) or \
                            (reserved_quant.package_id.id != operation.package_id.id):
                        continue
                    # ne pas traiter la quantité si elle est arrivée après la date de forçage
                    if force_date_done and reserved_quant.in_date and force_date_done < reserved_quant.in_date:
                        reserved_quant.reservation_id = False
                    elif not reserved_quant.lot_id:
                        false_quants += [reserved_quant]
                    elif float_compare(lot_quantities.get(reserved_quant.lot_id.id, 0), 0,
                                       precision_rounding=rounding) > 0:
                        if float_compare(lot_quantities[reserved_quant.lot_id.id], reserved_quant.qty,
                                         precision_rounding=rounding) >= 0:
                            qty_taken = min(reserved_quant.qty, qty_on_link)
                            lot_quantities[reserved_quant.lot_id.id] -= qty_taken
                            quants_taken += [(reserved_quant, qty_taken)]
                            qty_on_link -= qty_taken
                        else:
                            qty_taken = min(qty_on_link, lot_quantities[reserved_quant.lot_id.id])
                            quants_taken += [(reserved_quant, qty_taken)]
                            lot_quantities[reserved_quant.lot_id.id] -= qty_taken
                            qty_on_link -= qty_taken
                lot_move_qty[move.id] = qty_on_link

            remaining_move_qty[move.id] -= prout_move_qty[move]

        # Handle lots separately
        if operation.pack_lot_ids:
            # TDE FIXME: fix call to move_quants_by_lot to ease understanding
            self._move_quants_by_lot(operation, lot_quantities, quants_taken, false_quants, lot_move_qty,
                                     quant_dest_package_id)

        # Handle pack in pack
        if not operation.product_id and operation.package_id \
                and operation.result_package_id.id != operation.package_id.parent_id.id:
            operation.package_id.sudo().write({'parent_id': operation.result_package_id.id})

    # Check for remaining qtys and unreserve/check move_dest_id in
    move_dest_ids = set()
    for move in self:
        # In case no pack operations in picking
        if float_compare(remaining_move_qty[move.id], 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
            move.check_tracking(False)  # TDE: do in batch ? redone ? check this

            preferred_domain_list = [[('reservation_id', '=', move.id)], [('reservation_id', '=', False)],
                                     ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]]
            quants = Quant.quants_get_preferred_domain(
                remaining_move_qty[move.id], move, domain=[('qty', '>', 0)],
                preferred_domain_list=preferred_domain_list)
            Quant.quants_move(
                quants, move, move.location_dest_id,
                lot_id=move.restrict_lot_id.id, owner_id=move.restrict_partner_id.id)

        # If the move has a destination, add it to the list to reserve
        if move.move_dest_id and move.move_dest_id.state in ('waiting', 'confirmed'):
            move_dest_ids.add(move.move_dest_id.id)

        if move.procurement_id:
            procurements |= move.procurement_id

        # unreserve the quants and make them available for other operations/moves
        move.quants_unreserve()

    # Check the packages have been placed in the correct locations
    self.mapped('quant_ids').filtered(lambda quant: quant.package_id and quant.qty > 0).mapped(
        'package_id')._check_location_constraint()

    # OF début modification openfire
    date_done = force_date_done and force_date_done + " 12:00:00" or time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    # set the move as done
    self.write({'state': 'done', 'date': date_done})
    # OF fin modification openfire

    procurements.check()
    # assign destination moves
    if move_dest_ids:
        # TDE FIXME: record setise me
        self.browse(list(move_dest_ids)).action_assign()

    # OF début modification openfire
    # au moment de la création d'un reliquat, le picking associé au move est partiellement disponible ou confirmé
    pickings.filtered(
        lambda picking: picking.state in ('done', 'partially_available', 'confirmed') and not picking.date_done
    ).write({'date_done': date_done})
    # OF fin modification openfire

    return True


StockMove.action_done = action_done


class Inventory(models.Model):
    _inherit = "stock.inventory"
    _order = "date desc, name"

    date = fields.Datetime(readonly=False)
    of_option = fields.Boolean('Peut forcer la date', compute="_compute_of_option")
    category_child_ids = fields.Many2many(
        string=u"Catégories filles", comodel_name='product.category', compute='_compute_category_child_ids')
    of_performance_mode = fields.Boolean(string=u"Mode performance")
    of_category_ids = fields.Many2many(
        comodel_name='product.category', string='Inventoried Categories', readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Product Category to focus your inventory on a particular Category."
    )
    of_category_compute = fields.Boolean(string=u"Has categories", compute='_compute_of_category_compute')
    of_brand_ids = fields.Many2many(comodel_name='of.product.brand', string=u"Inventoried Brands")
    of_brand_compute = fields.Boolean(string=u"Has brands", compute='_compute_of_brand_compute')
    of_quant_state = fields.Selection(
        selection=[('all', u"All"), ('unreserved', u"Unreserved")], string=u"Reservation state",
        default='all', required=True
    )

    @api.depends('company_id')
    def _compute_of_option(self):
        option = self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_inventaire')
        for inventory in self:
            inventory.of_option = option

    @api.depends('category_id')
    def _compute_category_child_ids(self):
        categ_obj = self.env['product.category']
        for inventory in self:
            if inventory.category_id:
                children = categ_obj.search([
                    ('id', 'child_of', inventory.category_id.id),
                    ('id', '!=', inventory.category_id.id)])
            else:
                children = categ_obj
            inventory.category_child_ids = children.ids

    @api.depends('of_category_ids')
    def _compute_of_category_compute(self):
        for inventory in self:
            if inventory.of_category_ids:
                inventory.of_category_compute = True

    @api.depends('of_brand_ids')
    def _compute_of_brand_compute(self):
        for inventory in self:
            if inventory.of_brand_ids:
                inventory.of_brand_compute = True

    @api.multi
    def action_check(self):
        u"""
        Modification de la fonction définie dans le module stock
        Appel de _generate_moves() sur l'ensemble des lignes plutôt que sur les lignes 1 par 1
          permettra de gérer les doublons
        """
        for inventory in self:
            inventory.mapped('move_ids').unlink()
            inventory.line_ids._generate_moves()

    @api.multi
    def action_done(self):
        if self.of_performance_mode:
            self.toggle_mode()
        inventory_date = self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_inventaire')
        self = self.with_context(inventory_date=inventory_date)
        if self._uid != SUPERUSER_ID:
            negative = next((line for line in self.mapped('line_ids') if
                             line.product_qty < 0 and line.product_qty != line.theoretical_qty), False)
            if negative:
                raise UserError(_('You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s') %
                                (negative.product_id.name, negative.product_qty))
        self.action_check()
        self.write({'state': 'done'})
        if inventory_date:
            for inv in self:
                inv.with_context(default_datetime=inv.date).post_inventory()
        else:
            self.post_inventory()
        return True

    @api.multi
    def action_compile_lines(self):
        self.ensure_one()
        for line in self.line_ids:
            if line.exists() and not line.prod_lot_id and line.product_id.tracking == 'none':
                other_lines = self.line_ids.filtered(
                    lambda l: l.id != line.id and l.product_id == line.product_id and not l.prod_lot_id)
                if other_lines:
                    line.product_qty = line.product_qty + sum(other_lines.mapped('product_qty'))
                    other_lines.unlink()
        return True

    @api.multi
    def reset_real_qty(self):
        # On n'appelle pas le super, car on change le comportement du bouton
        category_ids = self.line_ids.mapped('product_id').mapped('categ_id').ids
        wizard = self.env['of.stock.inventory.reset.qty.wizard'].create({
            'stock_inventory_id': self.id,
            'product_category_ids': [(6, 0, category_ids)],
        })
        context = self.env.context.copy()
        context.update({
            'domain_category_ids': category_ids,
        })
        return {
            'name': u"Mettre les quantités des catégories à 0",
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': wizard.id,
            'res_model': 'of.stock.inventory.reset.qty.wizard',
            'type': 'ir.actions.act_window',
            'context': context,
        }

    @api.multi
    def create_missing_lines(self):
        self.ensure_one()
        category_ids = self.line_ids.mapped('product_id').mapped('categ_id').ids
        wizard = self.env['of.stock.inventory.create.missing.wizard'].create({
            'stock_inventory_id': self.id,
            'product_category_ids': [(6, 0, category_ids)],
        })
        context = self.env.context.copy()
        return {
            'name': u"Créer les lignes manquantes à 0",
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': wizard.id,
            'res_model': 'of.stock.inventory.create.missing.wizard',
            'type': 'ir.actions.act_window',
            'context': context,
        }

    @api.multi
    def action_control(self):
        self.ensure_one()

        if self.of_performance_mode:
            self.toggle_mode()

        title = u"ATTENTION !!!\n\nCertaines lignes de l'inventaire vont empêcher sa validation.\n\n" \
                u"Voici une liste d'erreurs bloquantes :\n\n"
        message = u""
        for line in self.line_ids:
            if line.product_qty < 0 and line.product_qty != line.theoretical_qty:
                message += u"- Vous ne pouvez pas saisir une quantité négative sur une ligne d'inventaire : " \
                           u"%s - qté : %s (ID de la ligne : %s)\n" % \
                           (line.product_id.name, line.product_qty, line.id)
            if line.product_id.tracking in ('serial', 'lot'):
                if not line.prod_lot_id:
                    message += u"- Vous devez renseigner un lot/numéro de série pour l'article %s " \
                               u"(ID de la ligne : %s)\n" % \
                               (line.product_id.name, line.id)
                if line.product_id.tracking == 'serial' and \
                        float_compare(line.product_qty, line.theoretical_qty, 5) != 0:
                    if float_compare(line.product_qty, 1.0, 5) != 0 and float_compare(line.product_qty, 0.0, 5) != 0:
                        message += u"- Vous ne pouvez pas saisir une quantité différente de 0 ou 1 pour un article " \
                                   u"géré par numéro de série : %s (ID de la ligne : %s)\n" % \
                                   (line.product_id.name, line.id)
                    same_serial_lines = self.line_ids.filtered(
                        lambda l: l.product_id == line.product_id and l.prod_lot_id == line.prod_lot_id and
                        l.id < line.id)
                    if same_serial_lines:
                        message += u"- Vous ne pouvez pas saisir deux lignes avec le même article et le même numéro " \
                                   u"de série : %s - %s (ID de la ligne : %s)\n" % \
                                   (line.product_id.name, line.prod_lot_id.name, line.id)
                    if float_compare(line.product_qty, 0.0, 5) != 0:
                        other_quants = self.env['stock.quant'].sudo().search(
                            [('product_id', '=', line.product_id.id), ('lot_id', '=', line.prod_lot_id.id),
                             ('qty', '>', 0.0), ('location_id.usage', '=', 'internal')])
                        if other_quants:
                            message += u"- L'article %s avec le numéro de série %s est déjà présent en stock " \
                                       u"(ID de la ligne : %s)\n" % \
                                       (line.product_id.name, line.prod_lot_id.name, line.id)

        if message:
            raise UserError(title + message)
        else:
            raise UserError(u"Tout semble correct.")

    @api.multi
    def toggle_mode(self):
        for record in self:
            record.of_performance_mode = not record.of_performance_mode
            # On provoque le recalcul des champs quand on repasse en mode normal
            if not record.of_performance_mode:
                for line in record.line_ids:
                    line._compute_theoretical_qty()
                    line._onchange_product_info()

    @api.model
    def _selection_filter(self):
        filters = super(Inventory, self)._selection_filter()
        index = filters.index(('category', _('One product category')))
        filters.insert(index+1, ('categories', u"Sélectionner les catégories et les marques"))
        return filters

    @api.onchange('filter')
    def onchange_filter(self):
        res = super(Inventory, self).onchange_filter()
        if self.filter != 'categories':
            self.of_category_ids = False
            self.of_brand_ids = False
        return res


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"
    _order = "product_id, inventory_id, location_id, prod_lot_id"

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        cr.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'stock_inventory_line' AND column_name = 'of_theoretical_qty'")
        exists = bool(cr.fetchall())
        res = super(InventoryLine, self)._auto_init()
        if not exists:
            cr.execute("UPDATE stock_inventory_line SET of_theoretical_qty = theoretical_qty")
        return res

    of_note = fields.Text(string="Notes")
    of_theoretical_qty = fields.Float(string=u"Quantité théorique")
    of_product_lot_serial_management = fields.Boolean(string=u"Géré par lot/num. de série")
    of_product_lot_serial_management_copy = fields.Boolean(string=u"Géré par lot/num. de série (champ technique)")
    of_inventory_gap = fields.Float(string=u"Écart d'inventaire", compute='_compute_of_inventory_gap', store=True)
    of_product_brand_id = fields.Many2one(
        comodel_name='of.product.brand', string=u"Brand", related='product_id.brand_id', readonly=True)
    of_product_categ_id = fields.Many2one(
        comodel_name='product.category', string=u"Product category", related='product_id.categ_id', readonly=True)
    of_internal_serial_number = fields.Char(
        string=u"Numéro de série interne", readonly=True, related='prod_lot_id.of_internal_serial_number')

    @api.depends('of_theoretical_qty', 'product_qty')
    def _compute_of_inventory_gap(self):
        for line in self:
            line.of_inventory_gap = line.product_qty - line.of_theoretical_qty

    @api.multi
    def _write(self, vals):
        # Impossible de mettre à jour le référence/nom de l'article si présent
        # dans une ligne d'inventaire d'une autre société que la société courante de l'utilisateur.
        # Donc sudo pour bypasser les problèmes de droits.
        for key in vals.keys():
            if key not in ['product_name', 'product_code']:
                break
        else:
            self = self.sudo()
        if 'theoretical_qty' in vals:
            vals['of_theoretical_qty'] = vals['theoretical_qty']
        return super(InventoryLine, self)._write(vals)

    @api.onchange('product_id', 'product_qty')
    def _onchange_product_id_or_qty(self):
        if self.product_id and self.product_id.tracking != 'none':
            self.of_product_lot_serial_management = self.of_product_lot_serial_management_copy = True
        qty = self.product_qty
        if self.product_id and self.product_id.tracking == 'serial' and \
                float_compare(qty, 0.0, 0) and float_compare(qty, 1.0, 0):
            self.product_qty = self.theoretical_qty
            return {
                'warning': {
                    'title': 'Avertissement',
                    'message': u"Vous ne pouvez pas utiliser une quantité différente de 1 ou 0 pour un article géré "
                               u"par numéro de série.",
                }
            }

    @api.model
    def create(self, values):
        if 'of_product_lot_serial_management_copy' in values:
            values.update({'of_product_lot_serial_management': values.get('of_product_lot_serial_management_copy')})
        # Retrait de la contrainte sur les lignes d'inventaire
        return super(InventoryLine, self.with_context(of_inventory_line_check_double=False)).create(values)

    @api.multi
    def write(self, vals):
        if 'of_product_lot_serial_management_copy' in vals:
            vals.update({'of_product_lot_serial_management': vals.get('of_product_lot_serial_management_copy')})
        return super(InventoryLine, self).write(vals)

    @api.model
    def _of_get_groupby_params(self):
        return [
            'location_id',
            'prod_lot_id',
            'product_id',
            'partner_id',
            'package_id',
        ]

    def _generate_moves(self):
        moves = self.env['stock.move']
        Quant = self.env['stock.quant']

        # Modification OpenFire :
        # il faut regrouper les lignes d'inventaire par article, société, emplacement, lot, propriétaire, paquet
        grouped_lines = []
        grouped_lines_dict = {}
        params = self._of_get_groupby_params()
        option = self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_inventaire')
        # Le dernier paramètre est traité séparément, il ne contiendra pas un dictionnaire
        # mais l'indice des lignes d'inventaire dans grouped_lines
        last_param = params.pop()
        for line in self:
            d = grouped_lines_dict
            for param in params:
                d = d.setdefault(line[param], {})
            if line[last_param] in d:
                # Note : l'opérateur |= ne rajoute pas les ids dans l'élément existant mais crée un nouvel élément.
                # De ce fait, on ne peut pas avoir l'objet line à la fois dans grouped_lines et grouped_lines_dict
                # car la synchronisation ne se ferait pas
                grouped_lines[d[line[last_param]]] |= line
            else:
                d[line[last_param]] = len(grouped_lines)
                grouped_lines.append(line)

        for lines in grouped_lines:
            line = lines[0]
            line._fixup_negative_quants()
            # Calcul de la quantité totale, avec possibilité d'udm différentes...
            product_qty = 0.0
            for l in lines:
                if l.product_uom_id == line.product_uom_id:
                    product_qty += l.product_qty
                else:
                    product_qty += l.product_uom_id._compute_quantity(l.product_qty, line.product_uom_id)
            theoretical_qty = l.product_uom_id._compute_quantity(line.theoretical_qty, line.product_uom_id)

            # Code copié depuis la fonction d'origine (module stock)
            if float_utils.float_compare(theoretical_qty, product_qty, precision_rounding=line.product_id.uom_id.rounding) == 0:
                continue
            diff = line.theoretical_qty - product_qty
            if diff < 0:  # found more than expected
                vals = line._get_move_values(abs(diff), line.product_id.property_stock_inventory.id, line.location_id.id)
            else:
                vals = line._get_move_values(abs(diff), line.location_id.id, line.product_id.property_stock_inventory.id)
            move = moves.create(vals)

            optional_domain = []
            if option:
                optional_domain = [('in_date', '<=', line.inventory_id.date)]
            if diff > 0:
                domain = [('qty', '>', 0.0), ('package_id', '=', line.package_id.id), ('lot_id', '=', line.prod_lot_id.id), ('location_id', '=', line.location_id.id)]
                preferred_domain_list = [[('reservation_id', '=', False)], [('reservation_id.inventory_id', '!=', line.inventory_id.id)]]
                domain += optional_domain
                quants = Quant.quants_get_preferred_domain(move.product_qty, move, domain=domain, preferred_domain_list=preferred_domain_list)
                Quant.quants_reserve(quants, move)
            elif line.package_id:
                move.action_done()
                move.quant_ids.write({'package_id': line.package_id.id})
                quants = Quant.search([('qty', '<', 0.0), ('product_id', '=', move.product_id.id),
                                       ('location_id', '=', move.location_dest_id.id), ('package_id', '!=', False)] + optional_domain, limit=1)
                if quants:
                    for quant in move.quant_ids:
                        # To avoid we take a quant that was reconcile already
                        if quant.location_id.id == move.location_dest_id.id:
                            quant._quant_reconcile_negative(move)
        return moves

    @api.one
    @api.depends('location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id',
                 'inventory_id.date')
    def _compute_theoretical_qty(self):
        if self.inventory_id.of_performance_mode:
            return
        if not self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_inventaire'):
            return super(InventoryLine, self)._compute_theoretical_qty()
        theoretical_qty = self.of_get_stock_history()[0]
        if theoretical_qty and self.product_uom_id and self.product_id.uom_id != self.product_uom_id:
            theoretical_qty = self.product_id.uom_id._compute_quantity(theoretical_qty, self.product_uom_id)
        self.theoretical_qty = theoretical_qty

    @api.onchange(
        'location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id',
        'inventory_id.date')
    def _onchange_product_info(self):
        if self[0].inventory_id.of_performance_mode:
            return
        for line in self:
            # Dans un onchange, l'appel d'un champ compute force son recalcul même s'il est stored.
            self.of_theoretical_qty = line.theoretical_qty

    def of_get_stock_history(self):
        """
        :return: [quantité en stock, valeur de l'inventaire (coût)]
        :TODO: Ajouter des filtres pour les champs partner_id et package_id
        """
        if not self.product_id:
            return [0.0, 0.0]
        in_move_request = """
            SELECT  SQ.qty                      AS quantity
            ,       SQ.cost                     AS cost
            FROM    stock_quant                 SQ
            ,       stock_quant_move_rel        SQMR
            ,       stock_move                  SM
            ,       stock_location              SL1
            ,       stock_location              SL2
            ,       product_product             PP
            WHERE   SQMR.quant_id               = SQ.id
            AND     SM.id                       = SQMR.move_id
            AND     SM.location_dest_id         = SL1.id
            AND     SM.location_id              = SL2.id
            AND     PP.id                       = SM.product_id
            AND     SQ.qty                      > 0
            AND     SM.state                    = 'done'
            AND     SL1.usage                   IN ('internal', 'transit')
            AND     (NOT    (   SL2.company_id  IS NULL
                            AND SL1.company_id  IS NULL
                            )
                    OR      SL2.company_id      != SL1.company_id
                    OR      SL2.usage           NOT IN ('internal', 'transit')
                    )
            AND     SM.date                     <= %s
            AND     SL1.id                      = %s
            AND     PP.id                       = %s
        """
        out_move_request = """
            SELECT  -SQ.qty                     AS quantity
            ,       SQ.cost                     AS cost
            FROM    stock_quant                 SQ
            ,       stock_quant_move_rel        SQMR
            ,       stock_move                  SM
            ,       stock_location              SL1
            ,       stock_location              SL2
            ,       product_product             PP
            WHERE   SQMR.quant_id               = SQ.id
            AND     SM.id                       = SQMR.move_id
            AND     SM.location_dest_id         = SL1.id
            AND     SM.location_id              = SL2.id
            AND     PP.id                       = SM.product_id
            AND     SQ.qty                      > 0
            AND     SM.state                    = 'done'
            AND     SL2.usage                   IN ('internal', 'transit')
            AND     (NOT    (   SL2.company_id  IS NULL
                            AND SL1.company_id  IS NULL
                            )
                    OR      SL2.company_id      != SL1.company_id
                    OR      SL1.usage           NOT IN ('internal', 'transit')
                    )
            AND     SM.date                     <= %s
            AND     SL2.id                      = %s
            AND     PP.id                       = %s
        """

        if self.prod_lot_id:
            in_move_request += """
            AND     SQ.lot_id                   = %s
            """ % self.prod_lot_id.id
            out_move_request += """
            AND     SQ.lot_id                   = %s
            """ % self.prod_lot_id.id
        else:
            in_move_request += """
            AND     SQ.lot_id                   IS NULL
            """
            out_move_request += """
            AND     SQ.lot_id                   IS NULL
            """
        if self.inventory_id.of_quant_state == 'unreserved':
            in_move_request += """
            AND     SQ.reservation_id           IS NULL
            """
            out_move_request += """
            AND     SQ.reservation_id           IS NULL
            """

        self.env.cr.execute(
            """
                SELECT  SUM(quantity)
                ,       SUM(quantity * cost)
                FROM    (
                        %s
                        UNION ALL
                        %s
                        )                       AS FOO
            """ % (in_move_request, out_move_request),
            (self.inventory_id.date, self.location_id.id, self.product_id.id,
             self.inventory_id.date, self.location_id.id, self.product_id.id,))
        return self.env.cr.fetchone()

    def _get_quants(self):
        quants = super(InventoryLine, self)._get_quants()
        if self.inventory_id.of_quant_state == 'unreserved':
            quants = quants.filtered(lambda q: not q.reservation_id)
        return quants


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    of_forcer_date_inventaire = fields.Boolean(string='(OF) Date inventaire')
    of_forcer_date_move = fields.Boolean(string='(OF) Date transfert')
    group_of_bon_transfert_valorise = fields.Boolean(
        string=u"(OF) Bon de transfert valorisé", default=False,
        help=u"Afficher la valeur du mouvement de stock dans mes bons de livraison.",
        implied_group='of_stock.group_of_bon_transfert_valorise',
        group='base.group_system')

    pdf_mention_legale = fields.Text(
        string=u"(OF) Mentions légales", help=u"Sera affiché dans les BL"
    )
    group_stock_inventory_group_advanced_quant_inventory = fields.Selection([
        (0, u"Use all quantities from the selected stock location."),
        (1, u"Choose between all quantities and only unreserved quantities.")
        ], u"(OF) Stock inventory quantities",
        implied_group='of_stock.stock_inventory_group_advanced_quant_inventory')
    of_serial_management_company_ids = fields.Many2many(
        comodel_name='res.company', relation='config_settings_res_company_rel', column1='config_id',
        column2='company_id', string=u"(OF) Sociétés gérant la traçabilté interne",
        help=u"Sociétés pour lesquelles la gestion de la traçabilité interne et la "
             u"génération automatique des numéros de série est activée")

    @api.onchange('group_stock_production_lot')
    def _onchange_group_stock_production_lot(self):
        if self.group_stock_production_lot == 0:
            self.update({'of_serial_management_company_ids': [(6, 0, [])]})

    @api.multi
    def set_of_forcer_date_inventaire_defaults(self):
        return self.env['ir.values'].sudo().set_default(
                'stock.config.settings', 'of_forcer_date_inventaire', self.of_forcer_date_inventaire)

    @api.multi
    def set_of_forcer_date_move_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'stock.config.settings', 'of_forcer_date_move', self.of_forcer_date_move)

    @api.multi
    def set_pdf_mention_legale_defaults(self):
        return self.env['ir.values'].sudo().set_default(
            'stock.config.settings', 'pdf_mention_legale', self.pdf_mention_legale
        )

    @api.multi
    def set_of_serial_management_company_ids_defaults(self):
        # On met à jour les types d'opérations Réceptions des sociétés qui gère la traçabilité interne pour pouvoir
        # sélectionner un numéro de série préalablement créé dans les BR
        picking_types = self.env['stock.picking.type'].search([('code', '=', 'incoming')])
        picking_types.filtered(
            lambda p: p.sequence_id.company_id.id in self.of_serial_management_company_ids.ids).write(
            {'use_existing_lots': True})
        picking_types.filtered(
            lambda p: p.sequence_id.company_id.id not in self.of_serial_management_company_ids.ids).write(
            {'use_existing_lots': False})

        return self.env['ir.values'].sudo().set_default(
            'stock.config.settings', 'of_serial_management_company_ids', self.of_serial_management_company_ids.ids)


class StockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'

    of_price_unit = fields.Monetary(
        string=u"PU HT", readonly=True, currency_field='company_currency_id', compute='_compute_of_price_unit')
    of_amount_untaxed = fields.Monetary(
        string=u"Total HT", readonly=True, currency_field='company_currency_id', compute='_compute_of_amount_untaxed')
    company_currency_id = fields.Many2one(
        'res.currency', related='picking_id.company_id.currency_id', string=u"Company currency", readonly=True)
    of_editable_record = fields.Boolean(string=u"Ligne modifiable", compute='_compute_editable_record')

    @api.depends('linked_move_operation_ids.move_id.of_computed_price_unit')
    def _compute_of_price_unit(self):
        for pack in self:
            if len(pack.linked_move_operation_ids) == 1:
                pack.of_price_unit = pack.linked_move_operation_ids.move_id.of_computed_price_unit
            else:
                pack.of_price_unit = pack.product_id.lst_price

    @api.depends('linked_move_operation_ids.move_id.of_amount_untaxed')
    def _compute_of_amount_untaxed(self):
        for pack in self:
            if len(pack.linked_move_operation_ids) == 1:
                pack.of_amount_untaxed = pack.linked_move_operation_ids.move_id.of_amount_untaxed

    @api.depends('product_qty')
    def _compute_editable_record(self):
        picking_product_id = self.env['ir.values'].sudo().get_default(
            'of.intervention.settings', 'picking_product_id')
        for pack in self:
            pack.of_editable_record = pack.product_qty == 0 and pack.product_id.id == picking_product_id

    @api.multi
    def action_split_lots(self):
        action = super(StockPackOperation, self).action_split_lots()
        company_ids = self.env['ir.values'].get_default(
            'stock.config.settings', 'of_serial_management_company_ids') or []
        action['context'].update({'display_internal_serial_number': self.env.user.company_id.id in company_ids})
        return action
    split_lot = action_split_lots

    @api.multi
    def print_label(self):
        return self.env['report'].get_action(self.ids, 'of_website_portal_carrier.report_receipt_label')


class StockPackOperationLot(models.Model):
    _inherit = 'stock.pack.operation.lot'

    of_internal_serial_number = fields.Char(
        string=u"Numéro de série interne", readonly=True, related='lot_id.of_internal_serial_number')


class StockMove(models.Model):
    _inherit = 'stock.move'

    of_has_reordering_rule = fields.Boolean(
        string=u"Règle de stock", compute="_compute_of_of_has_reordering_rule",
        help=u"L'article dispose de règles de réapprovisionnement."
    )
    of_reserved_qty = fields.Float(
        string=u"Qté(s) réservée(s)", digits=dp.get_precision('Product Unit of Measure'), compute='_compute_of_qty')
    of_available_qty = fields.Float(
        string=u"Qté(s) dispo(s)", digits=dp.get_precision('Product Unit of Measure'), compute='_compute_of_qty')
    of_theoretical_qty = fields.Float(
        string=u"Qté(s) théorique(s)", digits=dp.get_precision('Product Unit of Measure'), compute='_compute_of_qty',
        help=u"Si une règle de stock est définie pour l'article avec une date limite de prévision, le stock théorique "
             u"est calculé à cette date ; sinon le stock théorique calculé est le stock théorique global de l'article")
    of_computed_price_unit = fields.Float(
        string=u"PU HT", compute="_compute_of_price_unit", inverse="_inverse_of_price_unit")
    of_price_unit = fields.Monetary(string=u"PU HT", currency_field='company_currency_id')
    of_amount_untaxed = fields.Monetary(
        string=u"Total HT", currency_field='company_currency_id', compute="_compute_of_amount_untaxed")
    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', string="Company currency", readonly=True)

    def _inverse_of_price_unit(self):
        for move in self:
            move.of_price_unit = move.of_computed_price_unit

    @api.onchange('product_id')
    def _onchange_of_price_unit(self):
        for move in self:
            if not move.origin:
                move.of_computed_price_unit = move.product_id.list_price

    @api.depends('origin')
    def _compute_of_price_unit(self):
        for move in self:
            if move.procurement_id.sale_line_id:
                move.of_computed_price_unit = move.procurement_id.sale_line_id.price_unit
                for link in move.linked_move_operation_ids:
                    link.operation_id._compute_of_price_unit()
            else:
                move.of_computed_price_unit = move.of_price_unit or move.product_id.list_price

    @api.depends('of_computed_price_unit', 'product_uom_qty')
    def _compute_of_amount_untaxed(self):
        for move in self:
            move.of_amount_untaxed = move.of_computed_price_unit * move.product_uom_qty

    @api.depends('product_id', 'product_id.type')
    def _compute_of_of_has_reordering_rule(self):
        for move in self:
            move.of_has_reordering_rule = move.product_id.nbr_reordering_rules > 0

    @api.depends('product_id', 'location_id')
    def _compute_of_qty(self):
        for move in self:
            if move.product_id:
                # Qté(s) réservée(s)
                reserved_quants = self.env['stock.quant'].search(
                    [('location_id', 'child_of', move.location_id.id), ('product_id', '=', move.product_id.id),
                     ('reservation_id', '=', move.id)])
                move.of_reserved_qty = sum(reserved_quants.mapped('qty'))

                # Qté(s) dispo(s)
                available_quants = self.env['stock.quant'].search(
                    [('location_id', 'child_of', move.location_id.id), ('product_id', '=', move.product_id.id),
                     ('reservation_id', '=', False)])
                move.of_available_qty = sum(available_quants.mapped('qty'))

                # Qté(s) théorique(s)
                product_context = dict(self._context, location=move.location_id.id)
                orderpoints = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', move.product_id.id)],
                                                                            limit=1)
                if orderpoints and orderpoints.of_forecast_limit:
                    product_context['of_to_date_expected'] = \
                        (datetime.today() + relativedelta(days=orderpoints.of_forecast_period)). \
                        strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                move.of_theoretical_qty = move.product_id.with_context(product_context).virtual_available
            else:
                move.of_reserved_qty = 0
                move.of_available_qty = 0
                move.of_theoretical_qty = 0

    @api.multi
    def write(self, vals):
        if self._context.get('inventory_date') and 'date' in vals:
            vals.pop('date')
        return super(StockMove, self).write(vals)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self._context.get('of_to_date_expected', False):
            domain += [('date_expected', '<=', self._context.get('of_to_date_expected'))]
        return super(StockMove, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model_cr_context
    def _auto_init(self):
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_stock')])
        cr = self._cr
        if module_self.latest_version < '10.0.1.1.0':
            # On crée les colonnes manuellement pour éviter le calcul sur toutes les lignes existantes (trop long)
            cr.execute("ALTER TABLE stock_quant ADD COLUMN of_brand_id integer")
            cr.execute("ALTER TABLE stock_quant ADD COLUMN of_categ_id integer")
            cr.execute("ALTER TABLE stock_quant ADD COLUMN of_partner_id integer")
        res = super(StockQuant, self)._auto_init()
        if module_self.latest_version < '10.0.1.1.0':
            # Calcul du champ of_brand_id manuel
            cr.execute("UPDATE stock_quant AS sq "
                       "SET of_brand_id = pt.brand_id "
                       "FROM product_product AS pp "
                       "INNER JOIN product_template AS pt ON pt.id=pp.product_tmpl_id "
                       "WHERE sq.product_id = pp.id")
            # Calcul du champ of_categ_id manuel
            cr.execute("UPDATE stock_quant AS sq "
                       "SET of_categ_id = pt.categ_id "
                       "FROM product_product AS pp "
                       "INNER JOIN product_template AS pt ON pt.id=pp.product_tmpl_id "
                       "WHERE sq.product_id = pp.id")
            # Calcul du champ of_partner_id manuel
            cr.execute("UPDATE stock_quant AS sq "
                       "SET of_partner_id = sp.partner_id "
                       "FROM stock_move AS sm "
                       "INNER JOIN stock_picking AS sp ON sp.id = sm.picking_id "
                       "WHERE sm.id = sq.reservation_id AND sp.partner_id IS NOT NULL")
        return res

    of_brand_id = fields.Many2one(
        comodel_name='of.product.brand', related='product_id.brand_id', string=u"Marque", store=True, readonly=True,
        compute_sudo=True)
    of_categ_id = fields.Many2one(
        comodel_name='product.category', related='product_id.categ_id',
        string=u"Catégorie d'article", store=True, readonly=True, compute_sudo=True)
    of_partner_id = fields.Many2one(
        comodel_name='res.partner', related='reservation_id.picking_id.partner_id',
        string=u"Adresse de destination du mouvement réservé associé", store=True, readonly=True, compute_sudo=True)
    of_internal_serial_number = fields.Char(
        string=u"Numéro de série interne", readonly=True, related='lot_id.of_internal_serial_number')
    of_contremarque_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire")

    @api.multi
    def write(self, vals):
        if self._context.get('contremarque') and vals.get('reservation_id'):
            stock_move_obj = self.env['stock.move']
            stock_move = stock_move_obj.browse(vals['reservation_id'])
            partner = stock_move.picking_id.partner_id
            if partner:
                vals['of_contremarque_id'] = partner.id
        res = super(StockQuant, self).write(vals)
        return res

    def _quants_get_reservation_domain(self, move, pack_operation_id=False, lot_id=False, company_id=False,
                                       initial_domain=None):
        force_date = self._context.get('force_date_done', False)
        if force_date:
            initial_domain = (initial_domain or [('qty', '>', 0.0)]) + [('in_date', '<=', force_date)]

        return super(StockQuant, self)._quants_get_reservation_domain(
            move, pack_operation_id, lot_id, company_id, initial_domain)

    @api.model
    def test_stock(self):
        """
        Test de cohérence des mouvements de stock avec les quants
        """
        move_obj = self.env['stock.move']
        locations = self.env['stock.location'].search([('usage', '=', 'internal')])

        moves_out = move_obj.search([('state', '=', 'done'), ('location_id', 'in', locations.ids)])
        moves_in = move_obj.search([('state', '=', 'done'), ('location_dest_id', 'in', locations.ids)])

        to_check = moves_out
        location_field = 'location_id'
        while to_check:
            move = to_check[0]
            location = move[location_field]
            move_pack = move_obj
            move_pack_new = move
            # On récupère tous les mouvements sortants et entrants liés à celui-ci par le biais des quants
            while move_pack != move_pack_new:
                move_pack = move_pack_new
                quants = move_pack.mapped('quant_ids')
                move_pack_new |= quants\
                    .mapped('history_ids')\
                    .filtered(lambda m: m.location_id == location or m.location_dest_id == location)
            move_pack_out = move_pack.filtered(lambda m: m.location_id == location)
            move_pack_in = move_pack.filtered(lambda m: m.location_dest_id == location)
            # Début des vérifs
            total_out = sum(move_pack_out.mapped('product_qty'))
            total_in = sum(move_pack_in.mapped('product_qty'))
            total_quant = sum(quant.qty for quant in quants if quant.location_id == location)
            if round(total_in - total_out, 2) != round(total_quant, 2):
                print u"Incohérence :", min(move_pack.mapped('create_date')), round(total_in - total_out, 2),\
                    round(total_quant, 2), move.id, move_pack, quants
                to_check -= move_pack
            else:
                to_check -= move
            if not to_check and location_field == 'location_id':
                to_check = moves_in
                location_field = 'location_dest_id'

    @api.model
    def test_move_quants(self):
        """
        Fonction qui vérifie que la somme des quants positifs d'un move sortant est égale à la quantité du move
        """
        for move in self.env['stock.move'].search([('state', '=', 'done')]):
            quant_qty = sum([quant.qty for quant in move.quant_ids if quant.qty > 0])
            if float_compare(quant_qty, move.product_qty, precision_rounding=move.product_id.uom_id.rounding):
                print\
                    move.write_date,\
                    u"Incohérence quantité sur move %s : %s (%s) vs %s (%s) vs %s - %s : precision %s"\
                    % (move.id, move.product_qty, move.product_uom_qty,
                       quant_qty, " + ".join(str(quant.qty) for quant in move.quant_ids),
                       sum(move.linked_move_operation_ids.mapped('qty')),
                       move.product_uom.name, move.product_uom.rounding)

    @api.model
    def test_quant_chain(self):
        """
        Fonction qui vérifie si les moves associés à un quant forment bien une chaîne
          et si l'emplacement final de la chaîne correspond bien à l'emplacement du quant
        """
        for quant in self.env['stock.quant'].search([]):
            loc_vals = {}
            increment = 1 if quant.qty > 0 else -1
            for move in quant.history_ids:
                loc_vals[move.location_id] = loc_vals.get(move.location_id, 0) - increment
                loc_vals[move.location_dest_id] = loc_vals.get(move.location_dest_id, 0) + increment
            cpt = 0
            loc_out = False
            loc_in = False
            for loc, v in loc_vals.iteritems():
                if v:
                    cpt += abs(v)
                    if cpt > 2:
                        print u"Incohérence de chaîne de mvts sur quant %s" % quant.id
                        break
                    if v == 1:
                        loc_out = loc
                    elif v == -1:
                        loc_in = loc
            else:
                if loc_out:
                    if loc_out != quant.location_id:
                        print u"Incohérence emplacement du quant %s : %s vs %s" %\
                              (quant.id, quant.location_id.id, loc_out.id)
                    elif loc_in.usage == 'internal' and quant.qty > 0 and not quant.propagated_from_id:
                        print u"Le quant provient d'un emplacement physique mais n'a pas de quant négatif associé : %s"\
                              % quant.id
                    elif loc_in.usage != 'internal' and quant.propagated_from_id:
                        print u"Le quant provient d'un emplacement virtuel mais a un quant négatif associé : %s"\
                              % quant.id
                else:
                    # Les mouvements du quant forment un circuit (emplacement de départ = emplacement d'arrivée)
                    if quant.location_id not in loc_vals:
                        print u"Incohérence emplacement final inexistant sur quant %s (circuit)" % quant.id
                    elif quant.location_id.usage == 'internal' and quant.qty > 0 and not quant.propagated_from_id:
                        print u"Le quant forme un circuit mais son emplacement final n'est pas virtuel : %s" % quant.id
                    elif quant.location_id.usage != 'internal' and quant.propagated_from_id:
                        print u"Le quant forme un circuit avec quant négatif associé, " \
                              u"mais son emplacement est virtuel : %s" % quant.id
                # Test de graphe disjoint
                # Ces erreurs montrent une incohérence, mais qui ne devrait pas avoir d'incidence négative sur
                # les stocks (un cycle n'a pas d'impact sur le stock, si le quant pointe sur un emplacement qui est
                #  en-dehors, ou sur un emplacement virtuel, il n'aura pas non-plus d'impact, donc intégrité respectée).
                if quant.qty < 0:
                    continue
                loc_moves = {}
                for move in quant.history_ids:
                    location_id = move.location_id.id
                    if location_id in loc_moves:
                        loc_moves[location_id].append(move)
                    else:
                        loc_moves[location_id] = [move]
                to_test = [loc_in and loc_in.id or loc.id]
                checked = to_test[:]
                while to_test:
                    for move in loc_moves.get(to_test.pop(), []):
                        if move.location_dest_id.id in checked:
                            continue
                        checked.append(move.location_dest_id.id)
                        to_test.append(move.location_dest_id.id)
                if len(checked) < len(loc_vals):
                    if loc_out:
                        print u"Le quant forme une chaîne et au moins un circuit disjoints : %s" % quant.id
                    else:
                        print u"Le quant forme plusieurs circuits disjoints : %s" % quant.id

    @api.model
    def _extract_greatest_chain(self, moves_dict, end_loc, nb_restricted_moves, move_start=False):
        u"""
        Retourne la plus grosse chaîne de mouvements de stocks menant à l'emplacement final demandé.
        :param moves_dict: Dictionnaire des mouvements de stock par emplacement de destination.
        :param end_loc: Emplacement de fin de la chaîne.
            On part de cet emplacement et on remonte les mouvements pour générer la chaîne.
        :param nb_restricted_moves: Nombre de mouvements ayant une restriction de lot (n° de série associé)
            La chaîne retournée doit avoir un nombre de mouvements à n° de série égal à 0 ou nb_restricted_moves
        :param move_start: Mouvement de départ d'une chaîne (car un quant négatif y est associé).
            Si on passe dessus, on s'arrête !
        :return: mouvements de stock, emplacement d'origine, nombre de mouvements restreints inclus
        """
        # Attention, récursivité interdite en python T_T
        # On voudrait un plc, parcours en largeur
        move_obj = self.env['stock.move']
        todo = [(move_obj, end_loc, 0, False)]
        result = (False, False, 0)
        while todo:
            moves, loc, nb_restrict, start_reached = todo.pop(0)
            potential_moves = moves_dict.get(loc.id, move_obj) - moves
            if start_reached or not potential_moves:
                # On retourne en priorité un résultat qui contient les mouvements restreints (liés à un n° de série)
                if nb_restrict == result[2] or nb_restrict == nb_restricted_moves:
                    result = (moves, loc, nb_restrict)
                continue
            for p_move in potential_moves:
                if p_move in moves:
                    continue
                todo.append((
                    moves + p_move,
                    p_move.location_id,
                    nb_restrict + bool(p_move.restrict_lot_id),
                    p_move == move_start))
        return result

    @api.multi
    def of_make_negative_quant(self, move_origin):
        rounding = move_origin.product_id.uom_id.rounding
        neg_qt = self.create({
            'product_id': self.product_id.id,
            'location_id': move_origin.location_id.id,
            'qty': float_round(-self.qty, precision_rounding=rounding),
            'cost': self.cost,
            'history_ids': [(4, move_origin.id)],
            'negative_move_id': move_origin.id,
            'in_date': self.in_date,
            'company_id': self.company_id.id,
            'lot_id': self.lot_id.id,
            'owner_id': self.owner_id.id,
        })
        self.propagated_from_id = neg_qt

    @api.model
    def action_of_repair_move_quants_quantities(self):
        """
        Cette fonction répare les quantités des stock.move et stock.quant quand elles ne sont pas cohérentes
        Dans ces cas, on cherche un stock.move.operation.link (réservation du mouvement de stock dans un stock.picking)
        Seuls deux cas de figure sont traités :
        - Si le quant a raison, on modifie la quantité du mouvement de stock
        - Si le mouvement de stock a raison ET que sa quantité est supérieure à celle des quants, on ajoute un quant
          de complément et éventuellement un quant négatif
        """
        move_obj = self.env['stock.move']
        quant_obj = self.env['stock.quant']

        sale_lines_to_recompute = self.env['sale.order.line']
        purchase_lines_to_recompute = self.env['purchase.order.line']
        for move in move_obj.search([('state', '=', 'done')]):
            quant_qty = sum([quant.qty for quant in move.quant_ids if quant.qty > 0])
            if float_compare(quant_qty, move.product_qty, precision_rounding=move.product_id.uom_id.rounding):
                # Plusieurs cas possibles
                # 1 - Si la quantité réservée donne raison au quant, c'est le mouvement de stock qui a tort
                if not float_compare(
                        quant_qty, sum(move.linked_move_operation_ids.mapped('qty')),
                        precision_rounding=move.product_id.uom_id.rounding):
                    # SQL pas top, mais la surcharge de write dans le module stock empêche de modifier la quantité
                    # d'un mouvement traité
                    self._cr.execute(
                        "UPDATE stock_move SET product_qty = %s, product_uom_qty = %s WHERE id = %s"
                        % (quant_qty,
                           move.product_id.uom_id._compute_quantity(quant_qty, move.product_uom),
                           move.id))
                    # Il faut recalculer les quantités des lignes de commande, mais le cache est périmé à cause
                    # de la modification en SQL.
                    # On va donc reléguer ce calcul à la fin et on nettoiera le cache avant de l'effectuer
                    sale_lines_to_recompute |= move.procurement_id.sale_line_id
                    purchase_lines_to_recompute |= move.purchase_line_id
                # 2 - Si la quantité réservée donne raison au mouvement de stock, c'est le quant qui a tort
                elif not float_compare(
                        move.product_qty, sum(move.linked_move_operation_ids.mapped('qty')),
                        precision_rounding=move.product_id.uom_id.rounding):
                    if move.product_qty > quant_qty:
                        quant_obj._quant_create_from_move(
                            float_round(
                                move.product_qty - quant_qty,
                                precision_rounding=move.product_id.uom_id.rounding),
                            move)
        move_obj.invalidate_cache(['product_uom_qty'])
        # Recalcul de la qté livrée de la commande client associée
        for sale_line in sale_lines_to_recompute:
            sale_line.qty_delivered = sale_line._get_delivered_qty()
        # Recalcul de la quantité de la commande fournisseur associée
        for purchase_line in purchase_lines_to_recompute:
            purchase_line.product_qty = sum(purchase_line.move_ids.mapped('product_uom_qty'))

    @api.model
    def action_of_repair_quant_chain(self):
        """ Identifie et répare les problèmes de chaîne sur les quants.
        Plusieurs problèmes possibles sont corrigés par cette fonction :
        - Si les mouvements de stock liés au quant ne forment pas un chemin continu, on crée des quants pour séparer
          ces mouvements en différents chemins continus
        - Correction de l'emplacement du quant s'il n'est pas cohérent avec ses mouvements de stock
        - Création/suppression/correction d'un quant négatif associé à un quant positif, au besoin
        """
        def repair_negative_quant(quant, location, move=False):
            def get_move():
                if move:
                    return move
                for mv in quant.history_ids:
                    if mv.location_id == location:
                        return mv
            if location.usage == 'internal':
                if not quant.propagated_from_id:
                    # Il manque un quant négatif
                    quant.of_make_negative_quant(get_move())
                else:
                    # Réparation du quant négatif si besoin
                    neg_quant = quant.propagated_from_id
                    vals = {}
                    if neg_quant.location_id != location:
                        vals['location_id'] = location.id
                    if neg_quant.negative_move_id.location_id != location:
                        move = get_move()
                        vals['negative_move_id'] = move.id
                        vals['history_ids'] = [(6, 0, [move.id])]
                    if vals:
                        neg_quant.write(vals)
            elif location.usage != 'internal' and quant.propagated_from_id:
                # Il y a un quant négatif en trop
                quant.propagated_from_id.unlink()

        quant_obj = self.env['stock.quant']
        new_quant_defaults = {
            'history_ids': False,
            'lot_id': False,
            'negative_move_id': False,
            'propagated_from_id': False,
            'reservation_id': False,
        }

        for quant in quant_obj.search([('qty', '>', 0)]):
            loc_vals = {}
            for move in quant.history_ids:
                loc_vals[move.location_id] = loc_vals.get(move.location_id, 0) - 1
                loc_vals[move.location_dest_id] = loc_vals.get(move.location_dest_id, 0) + 1
            loc_out = []
            loc_in = False
            for loc, v in loc_vals.iteritems():
                if v > 0:
                    loc_out += [loc] * v
                elif v < 0:
                    loc_in = loc
            if len(loc_out) > 1:
                # Il y a plusieurs emplacements finaux différents, la chaîne n'est donc pas respectée.
                # Il faut séparer les chaînes sur des quants distincts
                negative_quant = quant.propagated_from_id
                negative_move = negative_quant.negative_move_id
                nb_restricted_moves = 0
                moves_packs = []
                available_moves = quant.history_ids
                for loc_dest in loc_out:
                    # Dictionnaire des mouvements disponibles par emplacement de destination
                    moves_dict = {}
                    for move in available_moves:
                        if move.location_dest_id.id in moves_dict:
                            moves_dict[move.location_dest_id.id] += move
                        else:
                            moves_dict[move.location_dest_id.id] = move
                        if move.restrict_lot_id:
                            nb_restricted_moves += 1
                    # Extraction d'une chaîne
                    moves, loc_orig, nb_restrict = self._extract_greatest_chain(
                        moves_dict, loc_dest, nb_restricted_moves, negative_move)
                    if nb_restrict:
                        nb_restricted_moves = 0
                    if not moves:
                        raise UserError(
                            u"ERR_001 - La découpe des mouvements du quant a échoué. "
                            u"Probablement en raison d'un n° de série. "
                            u"quant : %s" % (quant.name_get(), ))
                    if loc_vals[loc_orig] >= 0:
                        raise UserError(
                            u"ERR_002 - Problème de calcul de chaîne. "
                            u"L'emplacement d'origine calculé ne semble pas correspondre."
                            u"quant: %s, orig: %s, moves: %s" % (quant.name_get(), loc_orig.name_get(), moves.ids))
                    loc_vals[loc_orig] += 1
                    moves_packs.append((moves, loc_orig, loc_dest, nb_restrict))
                    available_moves -= moves
                if available_moves:
                    raise UserError(
                        u"ERR_003 - Il reste des mouvements non affectés après la découpe du quant."
                        u"quant : %s, moves : %s" % (quant.name_get(), moves.ids))
                all_quants = []
                while len(moves_packs) > 1:
                    moves, loc_orig, loc_dest, nb_restrict = moves_packs.pop(moves_packs[0][2] != 0)
                    new_quant_data = quant.copy_data(new_quant_defaults)[0]
                    new_quant_data['history_ids'] = [(6, 0, moves.ids)]
                    new_quant_data['location_id'] = loc_dest.id

                    if negative_move.id == moves.ids[-1]:
                        # Un quant négatif est associé, qui alimente ce quant
                        new_quant_data['propagated_from_id'] = negative_quant.id
                        quant.propagated_from_id = False
                    if quant.reservation_id and quant.reservation_id in moves:
                        new_quant_data['reservation_id'] = quant.reservation_id.id
                        quant.reservation_id = False
                    new_quant = quant_obj.create(new_quant_data)
                    all_quants.append((new_quant, moves[-1]))
                    # Modification des réservations des opérations
                    op_links = moves.mapped('linked_move_operation_ids')\
                                    .filtered(lambda link: link.reserved_quant_id.id == quant.id)
                    if op_links:
                        op_links.write({'reserved_quant_id': new_quant.id})
                quant.history_ids = moves_packs[0][0]
                all_quants.append((quant, moves_packs[0][0][-1]))
                # Correction de l'emplacement du quant d'origine
                if quant.location_id != moves_packs[0][0][0].location_dest_id:
                    quant.location_id = moves_packs[0][0][0].location_dest_id
                for qt, move_orig in all_quants:
                    repair_negative_quant(qt, move_orig.location_id)
            else:
                # Le chaînage est correct, on vérifie l'emplacement du quant et les quants négatifs
                if loc_out:
                    if loc_out[0] != quant.location_id:
                        quant.location_id = loc_out[0]
                else:
                    # Les mouvements du quant forment un circuit (emplacement de départ = emplacement d'arrivée)
                    if quant.location_id not in loc_vals:
                        if quant.propagated_from_id:
                            # On prend l'emplacement du quant négatif associé, le cas échéant
                            quant.location_id = quant.propagated_from_id.location_id
                        else:
                            # Sinon, on prend un emplacement au hasard, si possible virtuel
                            for loc in loc_vals:
                                if loc.usage != 'internal':
                                    break
                            quant.location_id = loc
                    loc_in = quant.location_id

                repair_negative_quant(quant, loc_in)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_lot_serial_management = fields.Boolean(
        string=u"Géré par lot/num. de série", compute='_compute_of_lot_serial_management', store=True)
    of_delay = fields.Integer(string="Delivery Lead Time", related='seller_ids.delay', readonly=True)

    # Stock Product Localization
    of_product_posx = fields.Char(string=u"Corridor (X)")
    of_product_posy = fields.Char(string=u"Shelves (Y)")
    of_product_posz = fields.Char(string=u"Height (Z)")


    @api.depends('tracking')
    def _compute_of_lot_serial_management(self):
        for rec in self:
            if rec.tracking != 'none':
                rec.of_lot_serial_management = True
            else:
                rec.of_lot_serial_management = False


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def name_get(self):
        if self._context.get('show_only_default_code', False):
            result = []
            for product in self:
                result.append((product.id, '[%s]' % product.default_code))
            return result
        else:
            res = super(ProductProduct, self).name_get()
            return res


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    of_forecast_limit = fields.Boolean(
        string=u"Limite de prévision", help=u"Permet de définir une date limite pour les réapprovisionnements.")
    of_forecast_period = fields.Integer(
        string=u"Période de prévision",
        help=u"Nombre de jours pour définir la date limite.\n"
        u"Ex : 30 jour(s), ne prend en compte que les mouvements de stock jusqu'"
        u"à J+30 pour décider de créer un nouvel approvisionnement.")

    @api.onchange('of_forecast_limit')
    def onchange_of_forecast_limit(self):
        if not self.of_forecast_limit:
            self.of_forecast_period = 0


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    of_internal_serial_number = fields.Char(string=u"Numéro de série interne", readonly=True)

    @api.multi
    def name_get(self):
        location_id = self._context.get('prio_location_id')
        if location_id:
            result = []
            for prod_lot in self:
                est_prio = location_id in prod_lot.quant_ids.mapped('location_id').ids
                result.append((prod_lot.id, "%s%s%s" % ('' if est_prio else '(',
                                                        prod_lot.name,
                                                        '' if est_prio else ')')))
            return result
        return super(StockProductionLot, self).name_get()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        location_id = self._context.get('prio_location_id')
        if location_id:
            args = args or []
            res = super(StockProductionLot, self).name_search(
                name,
                args + [['quant_ids.location_id', '=', location_id]],
                operator,
                limit) or []
            limit = limit - len(res)
            res += super(StockProductionLot, self).name_search(
                name,
                args + [['id', 'not in', [r[0] for r in res]], '|', ['quant_ids.location_id', '!=', location_id],
                        ['quant_ids', '=', False]],
                operator,
                limit) or []
            return res
        return super(StockProductionLot, self).name_search(name, args, operator, limit)

    @api.multi
    def generate_missing_internal_serial_number(self):
        sequence_obj = self.env['ir.sequence']
        barcode_nomenclature_obj = self.env['barcode.nomenclature']
        production_lots = self.filtered(lambda l: not l.of_internal_serial_number)

        for lot in production_lots:
            next_by_code = sequence_obj.next_by_code('stock.lot.serial')
            ean13 = barcode_nomenclature_obj.sudo().sanitize_ean("%0.13s" % next_by_code)
            lot.of_internal_serial_number = ean13
