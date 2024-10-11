# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._check_tours_groups()
        return users

    def write(self, vals):
        vals = self._remove_reified_groups(vals)
        if "groups_id" in vals and not self.env.context.get("of_avoid_check_tours_groups"):
            users_saved_groups = {user: user.groups_id for user in self}

        result = super().write(vals)

        if "groups_id" in vals and not self.env.context.get("of_avoid_check_tours_groups"):
            self._handle_tour_groups_post_update(vals, users_saved_groups)
        return result

    def _handle_tour_groups_post_update(self, vals, user_saved_groups):
        """
        Handle the post-update logic for tour groups.

        Args:
            vals (dict): The dictionary containing the updated values.
            user_saved_groups (dict): A dictionary mapping users to their saved groups.

        Returns:
            None
        """
        manual_creation = self.env.ref("of_planning_tour.group_of_planning_tour_manual_creation")
        no_manual_creation = self.env.ref("of_planning_tour.group_of_planning_tour_no_manual_creation")
        groups_values = vals.get("groups_id", [])
        for gval in groups_values:
            for user in self.with_context(of_avoid_check_tours_groups=True):
                saved_user_groups = user_saved_groups[user]
                if isinstance(gval, tuple) and gval[1] in (manual_creation.id, no_manual_creation.id):
                    if gval[0] in [Command.LINK, Command.LINK.value]:
                        if gval[1] == manual_creation.id and no_manual_creation in saved_user_groups:
                            user.groups_id -= no_manual_creation
                        elif gval[1] == no_manual_creation.id and manual_creation in saved_user_groups:
                            user.groups_id -= manual_creation
                    elif gval[0] in [Command.UNLINK, Command.UNLINK.value]:
                        if gval[1] == manual_creation.id and no_manual_creation not in saved_user_groups:
                            user.groups_id += no_manual_creation
                        elif gval[1] == no_manual_creation.id and manual_creation not in saved_user_groups:
                            user.groups_id += no_manual_creation
        # Check if the user is not in both groups at the same time or if the user is not in any group
        self._check_tours_groups()

    def _check_tours_groups(self):
        """
        Check and update the tour groups for the user.

        Checks if the user is in both groups at the same time or if the user is not in any group.
        If he is in both groups, remove him from the default one (no manual creation).
        If he is not in any group, add him to the default one (no manual creation).
        """
        group_tour_manual_creation = self.env.ref("of_planning_tour.group_of_planning_tour_manual_creation")
        group_tour_no_manual_creation = self.env.ref("of_planning_tour.group_of_planning_tour_no_manual_creation")

        for user in self.with_context(of_avoid_check_tours_groups=True):
            if group_tour_manual_creation in user.groups_id and group_tour_no_manual_creation in user.groups_id:
                if user.id in group_tour_manual_creation.users.ids:
                    group_tour_no_manual_creation.users = [Command.unlink(user.id)]
                else:
                    group_tour_manual_creation.users = [Command.unlink(user.id)]
            elif (
                group_tour_no_manual_creation not in user.groups_id and group_tour_manual_creation not in user.groups_id
            ):
                user.groups_id += group_tour_no_manual_creation
