# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def write(self, vals):
        if 'users' in vals and not self.env.context.get('of_avoid_check_tours_groups'):
            tour_groups = self.env.ref('of_planning_tour.group_of_planning_tour_manual_creation') | self.env.ref(
                'of_planning_tour.group_of_planning_tour_no_manual_creation'
            )
            saved_users_data = {group.id: group.users.ids for group in self.filtered(lambda g: g in tour_groups)}
        res = super().write(vals)

        if 'users' in vals and not self.env.context.get('of_avoid_check_tours_groups'):
            self._handle_tour_group_update(saved_users_data)
        return res

    def _handle_tour_group_update(self, saved_vals):
        """
        Handle the update of a tour group.

        This method is responsible for updating the tour group based on the changes in the saved values.
        It determines the added and removed user IDs from the group and performs the necessary operations
        to update the inverse group accordingly.

        Args:
            saved_vals (dict): A dictionary containing the saved values for the group.

        Returns:
            None
        """
        group_tour_manual_creation = self.env.ref('of_planning_tour.group_of_planning_tour_manual_creation')
        group_tour_no_manual_creation = self.env.ref('of_planning_tour.group_of_planning_tour_no_manual_creation')
        for group in self:
            added_users_ids = set(group.users.ids) - set(saved_vals.get(group.id, []))
            removed_users_ids = set(saved_vals.get(group.id, [])) - set(group.users.ids)
            inverse_group = (
                group_tour_no_manual_creation if group == group_tour_manual_creation else group_tour_manual_creation
            )
            if added_users_ids or removed_users_ids:
                inverse_group.with_context(of_avoid_check_tours_groups=True).write(
                    {
                        'users': [
                            Command.unlink(user_id) for user_id in added_users_ids if user_id in inverse_group.users.ids
                        ]
                        + [
                            Command.link(user_id)
                            for user_id in removed_users_ids
                            if user_id not in inverse_group.users.ids
                        ]
                    }
                )
