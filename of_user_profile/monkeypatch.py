# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models

from odoo.addons.base.models.res_users import Users

# We are 🐒-patching the following methods :
#    - base.res_users.create()

_create_original = Users.create


class OFUserProfileHooks(models.AbstractModel):
    """When you use monkey patching, the code is executed when the module
    is in the addons_path of the Odoo server, even is the module is not
    installed ! In order to avoid the side-effects it can create,
    we create an AbstractModel inside the module and we test the
    availability of this Model in the code of the monkey patching below.
    """

    _name = "of.user.profile.hooks.installed"
    _description = "This model is used to test if the module is installed and avoid monkey patching side-effects."


@api.model_create_multi
def create(self, vals_list):
    if self.env.get("of.user.profile.hooks.installed") is None:
        return _create_original(self, vals_list)

    users = super(Users, self).create(vals_list)
    for user in users:
        # if partner is global we keep it that way
        if user.partner_id.company_id:
            user.partner_id.company_id = user.company_id
        if not user.of_is_user_profile and user.partner_id.active != user.active:
            user.partner_id.active = user.active
    return users


Users.create = create
