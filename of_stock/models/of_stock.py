# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, fields, models, _
from odoo.tools import float_utils
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_inventory import Inventory
from odoo.addons.stock.models.stock_quant import Quant


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
        categ_products = Product.search([('categ_id', '=', self.category_id.id)])
        domain += ' AND product_id = ANY (%s)'
        args += (categ_products.ids,)
        products_to_filter |= categ_products
    if hasattr(self, 'of_option') and self.of_option:
        domain += ' AND in_date <= %s'
        args += (self.date, )

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
    '''Create a quant in the destination location and create a negative
    quant in the source location if it's an internal location. '''
    force_date = self._context.get('inventory_date', False)
    price_unit = move.get_price_unit()
    location = force_location_to or move.location_dest_id
    rounding = move.product_id.uom_id.rounding
    vals = {
        'product_id': move.product_id.id,
        'location_id': location.id,
        'qty': float_round(qty, precision_rounding=rounding),
        'cost': price_unit,
        'history_ids': [(4, move.id)],
        'in_date': move.date if force_date else datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
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
    if lot_id and move.product_id.tracking == 'serial' and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
        if qty != 1.0:
            raise UserError(_('You should only receive by the piece with the same serial number'))

    # create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
    return self.sudo().create(vals)


Quant._quant_create_from_move = _quant_create_from_move


class Inventory(models.Model):
    _inherit = "stock.inventory"
    _order = "date desc, name"

    date = fields.Datetime(readonly=False)
    of_option = fields.Boolean('Peut forcer la date', compute="_compute_of_option")
    of_performance_mode = fields.Boolean(string=u"Mode performance")

    @api.depends('company_id')
    def _compute_of_option(self):
        option = self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_inventaire')
        for inventory in self:
            inventory.of_option = option

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
        return super(Inventory, self.with_context(
                inventory_date=self.env['ir.values'].get_default(
                        'stock.config.settings', 'of_forcer_date_inventaire'))).action_done()

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
    def create_missing_lines(self):
        self.ensure_one()

        locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
        self.env.cr.execute(
            """ SELECT      product_id
                ,           sum(qty)        as product_qty
                ,           location_id
                ,           lot_id          as prod_lot_id
                ,           package_id
                ,           owner_id        as partner_id
                FROM        stock_quant
                WHERE       location_id     in %s
                AND         company_id      = %s
                GROUP BY    product_id
                ,           location_id
                ,           lot_id
                ,           package_id
                ,           partner_id
            """, (tuple(locations.ids), self.company_id.id,))

        data = self.env.cr.dictfetchall()
        vals = []
        product_ids = self.line_ids.mapped('product_id').ids
        prod_lot_ids = self.line_ids.mapped('prod_lot_id').ids
        for product_data in data:
            if product_data['product_qty'] != 0:
                product_data['theoretical_qty'] = product_data['product_qty']
                product_data['product_qty'] = 0.0
                if product_data['product_id'] and product_data['product_id'] not in product_ids:
                    product_data['product_uom_id'] = self.env['product.product'].browse(
                        product_data['product_id']).uom_id.id
                    vals.append(product_data)
                elif product_data['prod_lot_id'] and product_data['product_id'] and \
                        product_data['prod_lot_id'] not in prod_lot_ids:
                    product_data['product_uom_id'] = self.env['product.product'].browse(
                        product_data['product_id']).uom_id.id
                    vals.append(product_data)

        if vals:
            self.write({'line_ids': [(0, 0, line_values) for line_values in vals]})
        return True

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
        # Le dernier paramètre est traité séparément, il ne contiendra pas un dictionnaire mais l'indice des lignes d'inventaire dans grouped_lines
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
                        if quant.location_id.id == move.location_dest_id.id:  # To avoid we take a quant that was reconcile already
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


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    of_forcer_date_inventaire = fields.Boolean(string='(OF) Date inventaire')

    @api.multi
    def set_of_forcer_date_inventaire_defaults(self):
        return self.env['ir.values'].sudo().set_default(
                'stock.config.settings', 'of_forcer_date_inventaire', self.of_forcer_date_inventaire)


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def write(self, vals):
        if self._context.get('inventory_date') and 'date' in vals:
            vals.pop('date')
        return super(StockMove, self).write(vals)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    of_transporter_id = fields.Many2one(string=u"Transporteur", comodel_name='res.partner')

    @api.multi
    def action_picking_send(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'stock.picking',
            'default_res_id': self.ids[0],
            'default_composition_mode': 'comment'
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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    of_lot_serial_management = fields.Boolean(
        string=u"Géré par lot/num. de série", compute='_compute_of_lot_serial_management', store=True)

    @api.depends('tracking')
    def _compute_of_lot_serial_management(self):
        for rec in self:
            if rec.tracking != 'none':
                rec.of_lot_serial_management = True
            else:
                rec.of_lot_serial_management = False


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

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
