odoo.define('of_crm.dashboard', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;
var SalesTeamDashboardView = require('sales_team.dashboard');
var KanbanView = require('web_kanban.KanbanView');

SalesTeamDashboardView.include({

    render: function() {
        var self = this;

        return this.fetch_data().then(function(result){
            self.show_demo = result && result.nb_opportunities === 0;

            var sales_dashboard = QWeb.render('of_crm.SalesDashboard', {
                widget: self,
                show_demo: self.show_demo,
                values: result,
            });
            KanbanView.prototype.render.apply(self);
            $(sales_dashboard).prependTo(self.$el);
        });
    },
    on_dashboard_action_clicked: function(ev){
        ev.preventDefault();

        var $action = $(ev.currentTarget);
        var action_name = $action.attr('name');
        var action_extra = $action.data('extra');
        var additional_context = {};

        // TODO: find a better way to add defaults to search view
        if (action_name === 'calendar.action_calendar_event') {
            additional_context.search_default_mymeetings = 1;
        } else if (action_name === 'of_crm.of_crm_next_activities_action') {
            if (action_extra === 'today') {
                additional_context.search_default_today = 1;
            } else if (action_extra === 'this_week') {
                additional_context.search_default_this_week = 1;
            } else if (action_extra === 'overdue') {
                additional_context.search_default_overdue = 1;
            }
        } else if (action_name === 'crm.action_your_pipeline') {
            if (action_extra === 'overdue') {
                additional_context['search_default_overdue'] = 1;
            } else if (action_extra === 'overdue_opp') {
                additional_context['search_default_overdue_opp'] = 1;
            }
        } else if (action_name === 'crm.crm_opportunity_report_action_graph') {
            additional_context.search_default_won = 1;
        }

        this.do_action(action_name, {additional_context: additional_context});
    },
});
});
