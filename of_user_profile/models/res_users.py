# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import SUPERUSER_ID, Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

SUPERUSER_ID_ADMIN = 2


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.depends("groups_id")
    def _compute_share(self):
        super()._compute_share()
        for user in self.filtered_domain([("of_is_user_profile", "=", True)]):
            user.share = True

    @api.model
    def _get_default_field_ids(self):
        return (
            self.env["ir.model.fields"]
            .search(
                [
                    ("model", "in", ("res.users", "res.partner")),
                    ("name", "in", ("action_id", "menu_id", "groups_id")),
                ]
            )
            .ids
        )

    of_superuser_id = fields.Integer(default=SUPERUSER_ID)
    of_is_user_profile = fields.Boolean(string="Is User Profile")
    of_user_profile_id = fields.Many2one(comodel_name="res.users", string="User Profile")
    of_user_ids = fields.One2many(
        comodel_name="res.users",
        inverse_name="of_user_profile_id",
        string="Linked users",
        domain=[("of_is_user_profile", "=", False)],
    )
    of_field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        relation="res_users_fields_rel",
        column1="user_id",
        column2="field_id",
        string="Fields to update",
        domain=[
            ("model", "in", ("res.users", "res.partner")),
            ("ttype", "not in", ("one2many",)),
            ("name", "not in", ("of_is_user_profile", "of_user_profile_id", "of_user_ids", "of_field_ids", "view")),
        ],
        default=_get_default_field_ids,
    )
    of_is_update_users = fields.Boolean(
        string="Update users after creation",
        default=lambda *a: True,
        help="If non checked, users associated to this profile will not be updated after creation",
    )
    of_users_count = fields.Integer(compute="_compute_users_count")

    _sql_constraints = [
        (
            "active_admin_check",
            "CHECK (id = 2 AND active = TRUE OR id <> 2)",
            "The user with id = 2 must always be active!",
        ),
        (
            "profile_without_profile_id",
            "CHECK( (of_is_user_profile = TRUE AND of_user_profile_id IS NULL) OR " "of_is_user_profile = FALSE )",
            "Profile users cannot be linked to a profile!",
        ),
    ]

    # --------------------------------------------------------------------------
    # Constrains methods
    # --------------------------------------------------------------------------

    @api.constrains("of_user_profile_id")
    def _check_of_user_profile_id(self):
        admins = self.env.ref("base.user_root") | self.env.ref("base.user_admin")
        for user in self:
            if user.of_user_profile_id in admins:
                raise ValidationError(_("You can't use %s as user profile !") % user.of_user_profile_id.name)

    # --------------------------------------------------------------------------
    # Compute methods
    # --------------------------------------------------------------------------

    @api.depends("of_user_ids")
    def _compute_of_users_count(self):
        for user in self:
            user.of_users_count = len(user.of_user_ids)

    # --------------------------------------------------------------------------
    # Onchange methods
    # --------------------------------------------------------------------------

    @api.onchange("of_is_user_profile")
    def onchange_of_is_user_profile(self):
        if self.of_is_user_profile:
            self.active = self.id in [SUPERUSER_ID, SUPERUSER_ID_ADMIN]
            self.of_user_profile_id = False

    # --------------------------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        create_from_profile = any(vals.get("of_is_user_profile", False) for vals in vals_list)
        users = super(ResUsers, self.with_context(from_create_profile=create_from_profile)).create(vals_list)
        for user in users.filtered(lambda user: user.of_user_profile_id):
            user._update_from_profile()
        return users

    def write(self, vals):
        if of_user_profile_id := vals.get("of_user_profile_id"):
            users_to_update = self.filtered(lambda user: user.of_user_profile_id.id != of_user_profile_id)
        vals = self._remove_reified_groups(vals)
        res = super().write(vals)
        if vals.get("of_user_profile_id"):
            users_to_update._update_from_profile()
        else:
            self._update_users_linked_to_profile(list(vals.keys()))
        return res

    # --------------------------------------------------------------------------
    # Business methods
    # --------------------------------------------------------------------------

    def _update_from_profile(self, fields=None):
        if not self:
            return
        if len(self.mapped("of_user_profile_id")) != 1:
            raise UserError(_("_update_from_profile accepts only users linked to a same profile"))
        user_profile = self[0].of_user_profile_id
        if not fields:
            fields = user_profile.of_field_ids.mapped("name")
        else:
            fields = set(fields) & set(user_profile.of_field_ids.mapped("name"))
        if user_profile:
            vals = {}
            for field in fields:
                value = user_profile[field]
                field_type = self._fields[field].type
                if field_type == "many2one":
                    vals[field] = value.id
                elif field_type == "many2many":
                    vals[field] = [Command.set(value.ids)]
                elif field_type == "one2many":
                    raise UserError(_("_update_from_profile doesn't manage fields.One2many"))
                else:
                    vals[field] = value
            if vals:
                self.write(vals)

    def _update_users_linked_to_profile(self, fields=None):
        for user_profile in self.filtered(lambda user: user.of_is_user_profile and user.of_is_update_users):
            user_profile.with_context(active_test=False).mapped("of_user_ids")._update_from_profile(fields)
