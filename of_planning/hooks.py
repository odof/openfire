from odoo import SUPERUSER_ID, api


def apply_domain_on_rule(env, ir_model_data, rule_ref, new_domain):
    """Update the domain of a "noupdate" rule with the given domain."""
    rule_data = env["ir.model.data"].search([("module", "=", "calendar"), ("name", "=", ir_model_data)])
    rule = env.ref(rule_ref)
    rule_data.noupdate = False
    rule.domain_force = new_domain
    rule_data.noupdate = True


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Init of_company_choice field
    env["res.company"].search([]).write({"of_company_choice": "contact"})

    # Apply new domain on calendar rules
    apply_domain_on_rule(
        env,
        "calendar_event_rule_employee",
        "calendar.calendar_event_rule_employee",
        "[('of_type', '=', 'event')]",
    )
    apply_domain_on_rule(
        env,
        "calendar_event_rule_private",
        "calendar.calendar_event_rule_private",
        "['|', ('of_type','=','intervention'), "
        "'&', ('of_type','=','event'), '|', ('privacy', '!=', 'private'), "
        "'&', ('privacy', '=', 'private'), '|', ('user_id', '=', user.id), "
        "('partner_ids', 'in', user.partner_id.id)]",
    )


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Restore original domains
    apply_domain_on_rule(
        env,
        "calendar_event_rule_employee",
        "calendar.calendar_event_rule_employee",
        "[(1, '=', 1)]",
    )
    apply_domain_on_rule(
        env,
        "calendar_event_rule_private",
        "calendar.calendar_event_rule_private",
        "['|', "
        "('privacy', '!=', 'private'), "
        "'&', ('privacy', '=', 'private'),"
        "'|',('user_id', '=', user.id), ('partner_ids', 'in', user.partner_id.id)]",
    )

    # Remove context from calendar action
    calendar_action = env.ref("calendar.action_calendar_event")
    calendar_action.write(
        {
            "context": "{}",
            "domain": "[]",
        }
    )
