odoo.define('of_timeline.TimelineView', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var data_manager = require('web.data_manager');
var Model = require('web.DataModel');
var View = require('web.View');
var Pager = require('web.Pager');
var pyeval = require('web.pyeval');
var session = require('web.session');
var utils = require('web.utils');
var ActionManager = require('web.ActionManager');
var map_controls = require('of_map_view.map_controls');
var map_utils = require('of_map_view.map_utils');
var Widget = require('web.Widget');
var QWeb = require('web.QWeb');
var mixins = core.mixins;
var formats = require('web.formats');
var time = require('web.time');
var local_storage = require('web.local_storage');

var CompoundDomain = data.CompoundDomain;

var _t = core._t;
var _lt = core._lt;
var qweb = core.qweb;

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
};

function hexToRgb(hex) {
  var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

var MODE_COLUMN_NBS = {
    "day": 1,
    "week": 7,
    "month": 7,
};
/*
NEXT: APPLY FILTERS ASYNC! fillerbars, event disponibles
TODO: events sur plusieurs jours: heures, ligne connectante: grouper connecrted divs
*/
var PlanningView = View.extend({
    template: 'PlanningView',
    display_name: _lt('Planning'),
    icon: 'fa fa-sliders',
    view_type: "planning",
    //className: "of_map_view",
    _model: null,
    defaults: _.extend({}, View.prototype.defaults, {
        // records can be selected one by one
        selectable: true,
        // records can be deleted
        deletable: false,
        // whether the column headers should be displayed
        header: true,
        // display addition button, with that label
        addable: _lt("Create"),
        // whether the list view can be sorted, note that once a view has been
        // sorted it can not be reordered anymore
        sortable: false,
        // whether the view rows can be reordered (via vertical drag & drop)
        reorderable: true,
        action_buttons: true,
        // whether the editable property of the view has to be disabled
        disable_editable_mode: false,
        auto_search: false, // the search is done when the map is attached. See MapView.Map.on_map_attached. Apparently not taken into account D:
    }),
    events: {
        'click .of_planning_sidebar_toggler': 'toggle_full_width',
    },
    custom_events: {
        'all_rows_rendered': 'on_all_rows_rendered',
    },
    /*custom_events: {
        'timeline_inited': 'on_timeline_inited',
    },
    /*custom_events: {
        'timeline_record_open': 'open_record',
        'timeline_do_action': 'open_action',
    },*/
    /**
     *
     */
    init: function (parent, dataset, view_id, options) {
        this._super.apply(this, arguments);
        var attrs = this.fields_view.arch.attrs;
        if (!attrs.date_start) {
            throw new Error(_t("Planning view has not defined 'date_start' attribute."));
        }
        if (!attrs.resource) {
            throw new Error(_t("Planning view has not defined 'resource' attribute."));
        }
        this.resource = attrs.resource;
        this.color_ft = attrs.color_ft;
        this.color_bg = attrs.color_bg;
        this.fields = this.fields_view.fields;
        this.fields_keys = _.keys(this.fields_view.fields);
        this.name = this.fields_view.name || attrs.string;
        this.rows = {}; // dict of events {id1: [ev1,ev2], id2: [ev3], ..}
        
        this.date_start = attrs.date_start;     // Field name of starting date field
        this.date_delay = attrs.date_delay;     // duration
        this.date_stop = attrs.date_stop;
        this.all_day = attrs.all_day;

        this.mode = attrs.mode || options.mode || "week";  // one of month, week or day
        this.column_nb = MODE_COLUMN_NBS[this.mode];
        this.range_start = moment().startOf(this.mode)._d;
        this.range_stop = moment().endOf(this.mode)._d;
        this.planning_table = false;
        this.set_columns();

        this.shown = $.Deferred();
        //this.cmptry = 0;
        //this.planning_inited = false;

        this.info_fields = [];
        for (var fld = 0; fld < this.fields_view.arch.children.length; fld++) {
            if (isNullOrUndef(this.fields_view.arch.children[fld].attrs.invisible)) {
                this.info_fields.push(this.fields_view.arch.children[fld].attrs.name); // don't add field to description if invisible="1"
            }
        }
        console.log("PLANNING VIEW THIS: ",this);
    },
    /**
     *
     */
     willStart: function () {
        console.log("WILLSTART");
        var self = this;
        var write_def = this.dataset.call("check_access_rights", ["write", false]);
        var create_def = this.dataset.call("check_access_rights", ["create", false]);
        var rendered_prom = this.$el.html(qweb.render(this.template, this)).promise();
        return $.when(write_def, create_def, rendered_prom, this._super()).then(function (write, create) {
            self.write_right = write;
            self.create_right = create;
        });
    },
    /**
     *
     */
    start: function () {
        console.log("START");
        //var options = {'debug': true};
        //var la_div = this.$(".of_timeline_widget");
        this.$sidebar_container = this.$(".of_planning_sidebar_container");
        this.$table_container = this.$(".of_planning_table_container");
        this.$el.addClass(this.fields_view.arch.attrs.class);
        this.shown.done(this.init_table.bind(this));
        return this._super();
    },
    /*_do_show_init: function () {
        this.init_planning().then(function() {
            $(window).trigger('resize');
        });
    },*/

    do_show: function() {
        this.do_push_state({});
        this.shown.resolve();
        return this._super();
    },
    init_table: function() {
        var self = this;
        this.table = new PlanningView.Table(this);
        var defs = [];
        if (!this.sidebar) {
            this.sidebar = new PlanningView.Sidebar(this);
            defs.push(this.sidebar.appendTo(this.$sidebar_container));

            //var le_dateFormat = "MM/DD/YY"//time.strftime_to_moment_format(_t.database.parameters.date_format);
            //console.log("le_dateFormat.toLowerCase():",le_dateFormat.toLowerCase());

            this.$small_calendar = this.$(".of_planning_calendar_mini");
            this.$small_calendar.datepicker({ 
                onSelect: this.calendarMiniChanged(this),
                dayNamesMin : moment.weekdaysShort(),
                monthNames: moment.monthsShort(),
                firstDay: moment()._locale._week.dow,
                //dateFormat: le_dateFormat.toLowerCase(),
            });
            //console.log("moment(this.range_start).format(le_dateFormat):",moment(this.range_start).format(le_dateFormat));
            //this.$small_calendar.datepicker("setDate",moment(this.range_start).format(le_dateFormat));
            //this.$small_calendar.datepicker("setDate","06/10/2019");
            //console.log("dpoption dateformat:",this.$small_calendar.datepicker("option","dateFormat"));
            
            //this.$small_calendar.datepicker("_setDate",this.$small_calendar.datepicker("_getInst"),this.range_start,true);

            defs.push(this.extraSideBar());

            // Add show/hide button and possibly hide the sidebar
            this.$sidebar_container.append($('<i>').addClass('of_planning_sidebar_toggler fa'));
            this.toggle_sidebar((local_storage.getItem('web_calendar_full_width') !== 'true'));
        }
        return $.when.apply($, defs)
        .then(function () {
            self.table_inited = true;
            self.do_search(this.domain,this.context,this.group_by);
        });
    },
    calendarMiniChanged: function (context) {
        //TODO adapt
        console.log("OOOOOOOOOOOOOOOOOO calendarMiniChanged!")
        return function(datum,obj) {
            console.log("datum:",datum);
            console.log("obj:",obj);
            var curMode = context.mode;
            var curDate = new Date(obj.currentYear , obj.currentMonth, obj.currentDay);

            if (curMode == "week") {
                if (curDate <= context.range_stop && curDate >= context.range_start) {  // day of same week
                    console.log("that doesn't do anything...")
                    //context.$calendar.fullCalendar('changeView','agendaDay');
                }else{
                    context.range_start = moment(curDate).startOf("week")._d;
                    context.range_stop = moment(curDate).endOf("week")._d;
                    console.log("new range!",context.range_start,context.range_stop);
                    context.do_search(context.domain,context.context,context.group_by);
                }
            }

            /*var curView = context.$calendar.fullCalendar('getView');
            var curDate = new Date(obj.currentYear , obj.currentMonth, obj.currentDay);

            if (curView.name == "agendaWeek") {
                if (curDate <= curView.end && curDate >= curView.start) {
                    context.$calendar.fullCalendar('changeView','agendaDay');
                }
            }
            else if (curView.name != "agendaDay" || (curView.name == "agendaDay" && moment(curDate).diff(moment(curView.start))===0)) {
                context.$calendar.fullCalendar('changeView','agendaWeek');
            }
            context.$calendar.fullCalendar('gotoDate', obj.currentYear , obj.currentMonth, obj.currentDay);*/
        };
    },
    extraSideBar: function() {
        return $.when();
    },
    toggle_full_width: function () {
        var full_width = (local_storage.getItem('web_calendar_full_width') !== 'true');
        local_storage.setItem('web_calendar_full_width', full_width);
        this.toggle_sidebar(!full_width);
        //this.$calendar.fullCalendar('render'); // to reposition the events
    },
    toggle_sidebar: function (display) {
        this.sidebar.do_toggle(display);
        this.$('.of_planning_sidebar_toggler')
            .toggleClass('fa-close', display)
            .toggleClass('fa-chevron-left', !display)
            .attr('title', display ? _('Close Sidebar') : _('Open Sidebar'));
        this.$sidebar_container.toggleClass('of_sidebar_hidden', !display);
    },
    do_search: function (domain, context, group_by) {
        //console.log("MapView.do_search: ",arguments);
        var self = this;
        this.domain = domain;
        this.context = context;
        this.group_by = group_by;
        
        if (this.table_inited) {
            this._do_search(domain, context, group_by);
        }else{
            console.log('do_search not done, timeline not inited');
        }
    },
    _do_search: function(domain, context, group_by) {
        var self = this;
        var la_key;
        if (! self.all_filters) {
            self.all_filters = {};
        }
        var event_domain = self.get_range_domain(this.domain || [],this.range_start,this.range_stop);
        self.dataset.read_slice(self.fields_keys, {
                    offset: 0,
                    domain: event_domain,
                    context: context,
            }).done(function(events) {
                self.now_filter_ids = [];
                self.rows = {};
                self.set_columns();
                if (events.length >0) {
                    console.log("events: ",events);
                    //console.log("self.resource: ",self.resource);
                    //console.log("events[0][self.resource]: ",events[0][self.resource]);
                    
                    var filter_item;
                    var event, planning_record, day_span, col_offset_start, col_offset_stop, record_options, row_options;
                    for (var i=0; i<events.length; i++) {
                        event = events[i];
                        // how many days?
                        day_span = moment(event[self.date_stop]).startOf('day').diff(moment(event[self.date_start]).startOf('day'), 'days')+1;
                        //console.log("EVENT:",event);
                        //console.log("DAY SPAN:",day_span);
                        if (day_span > 1) {
                            col_offset_stop = moment(event[self.date_stop]).startOf('day').diff(moment(self.range_start), 'days');
                        }else{
                            col_offset_stop = undefined;
                        }
                        //console.log("duration: ",day_span);
                        // the column index to insert the record
                        col_offset_start = moment(event[self.date_start]).startOf('day').diff(moment(self.range_start), 'days');
                        if (col_offset_start < 0) {
                            console.log("TROP TOT")
                        }else if (col_offset_start >= self.column_nb) {
                            console.log("TROP TARD");
                        }
                        record_options = {
                            "col_offset_start": col_offset_start,
                            "col_offset_stop": col_offset_stop,
                            "color_bg": event[self.color_bg] || "#7FFF00",
                            "color_ft": event[self.color_ft] || "#0C0C0C",
                            "day_span": day_span,
                        }
                        //console.log("col_offset_start: ",col_offset_start);
                        planning_record = new PlanningRecord(self,event,record_options);
                        //console.log("event: ",event);
                        la_key = event[self.resource][0];
                        if (!self.all_filters[la_key]) {
                            filter_item = {
                                value: la_key,
                                input_id: la_key + "_input",
                                label: event[self.resource][1],
                                //color: self.get_color(key),
                                //avatar_model: (utils.toBoolElse(self.avatar_filter, true) ? self.avatar_filter : false ),
                                is_checked: true,
                            };
                            self.all_filters[la_key] = filter_item;
                        };
                        if (! _.contains(self.now_filter_ids, la_key)) {
                            self.now_filter_ids.push(la_key);
                        };
                        if (!self.rows[la_key]) {
                            row_options = {
                                "res_id": event[self.resource][0],
                                "head_column": event[self.resource][1],
                                "color_bg": event[self.color_bg] || "#7FFF00",
                                "color_ft": event[self.color_ft] || "#0C0C0C",
                                "auto_render": false,
                            }
                            self.rows[la_key] = new PlanningView.Row(self.table,self,[planning_record],row_options);
                        }else{
                            self.rows[la_key].add_record(planning_record);
                        }
                    }
                }

                if (self.sidebar) {
                    self.sidebar.reso_filter.render();
                    /*if (self.sidebar.info_filter.rendered) {
                        console.log("ALREADY RENDERED!");
                        self.sidebar.info_filter.apply_filters();
                    }else{
                        self.sidebar.info_filter.render(); //@TODO: trouver un meilleur endroit pour faire ça!//
                    }*/
                    
                    //console.log("self.now_filter_ids:",self.now_filter_ids);
                    for (var key in self.rows) {
                        var key_num = Number(key);
                        if (_.include(self.now_filter_ids, key_num) &&  self.all_filters[key_num].is_checked) {
                            self.rows[key].hidden = false;
                        }else{
                            self.rows[key].hidden = true;
                        }
                    }
                }
                console.log("self.rows: ",self.rows);
                
                self.table.rows = self.rows;
                self.render_table();
            });
    },
    /**
     *  called by PlanningView.get_all_filters_ordered
     *  sets custom colors for all_filter.
     */
    _set_all_custom_colors: function() {
        var self = this;
        var ids = _.reject(_.keys(self.all_filters),function(num){ return num == 'undefined'; });

        var dfd = $.Deferred();
        var p = dfd.promise({target: kays});
        var kays = [];
        var model_name = self.fields[self.resource].relation;
        console.log("MODEL NAME:",model_name);

        var Attendees = new Model(model_name);
        Attendees.query(['id', self.color_ft, self.color_bg]) // retrieve colors from db
            .filter([['id','in',ids]]) // id
            .all()
            .then(function (attendees){
                for (var i=0; i<attendees.length; i++) {
                    var a = attendees[i];
                    var key = a.id;
                    kays.push(key);
                    self.all_filters[key]['color_bg'] = a[self.color_bg];
                    self.all_filters[key]['color_ft'] = a[self.color_ft];
                };
                dfd.resolve();
            });

        return $.when(p).then(function(){
            return kays;
        });
    },
    /**
     *  Adds custom colors to filters.
     *  called by SidebarResoFilter.render()
     */
    get_all_filters_ordered: function() {
        var self = this
        var filters = _.values(this.all_filters).sort(function(f1,f2) {
            return _.string.naturalCmp(f1.label, f2.label);
        });
        var dfd = $.Deferred();
        var p = dfd.promise({target: filters});
        $.when(self._set_all_custom_colors()).then(function(kays) {
                /*for (var i=0; i<filters.length; i++) { // doesn't work somehow. doesn't need to work apparently
                    if (filters[i].value in kays) {
                        var index = filters[i].value;
                        filters[i]['color_bg'] = self.all_filters[index].color_bg;
                        filters[i]['color_ft'] = self.all_filters[index].color_ft;
                        filters[i]['custom_colors'] = true;
                    }
                }*/
                dfd.resolve();
            });

        return p;
    },
    render_table: function() {
        var self = this;
        console.log("render_table");
        var rendered_prom = this.$(".of_planning_table").html(qweb.render("PlanningView.table", {"table": this.table})).appendTo(self.$table_container).promise();

        return $.when(rendered_prom)
            /*.then(function() {
                return true//self.$(".of_planning_table").replaceAll("table");
            })*/
            .then(function () {  // render rows
                //var rows_rendered = $.Deferred();
                _.each(self.rows, function(row) {
                    row.render();
                });
                //return rows_rendered.promise();
            })  // apply info_filters
            /*.then(function() {
                if (self.sidebar) {
                    if (self.sidebar.info_filter.rendered) {
                        console.log("ALREADY RENDERED!");
                        self.sidebar.info_filter.apply_filters();
                    }else{
                        self.sidebar.info_filter.render();
                    }
                }
            })*/;
    },
    /**
     * Render the buttons according to the TimelineView.buttons template and
     * add listeners on it.
     * Set this.$buttons with the produced jQuery element
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case the ListView inserts them into this.options.$buttons
     * or into a div of its template
     */
    render_buttons: function($node) {
        console.log("RENDER BUTTONS");
        var self = this;
        this.$buttons = $(qweb.render("PlanningView.buttons", {'widget': this}));
        this.$buttons.on('click', 'button.of_planning_button_new', function () {
            self.dataset.index = null;
            self.do_switch_view('form');
        });

        this.$buttons.find(".of_planning_button_prev").click(
            this.proxy(self.on_prev_clicked));
        this.$buttons.find(".of_planning_button_today").click(
            this.proxy(self.on_today_clicked));
        this.$buttons.find(".of_planning_button_next").click(
            this.proxy(self.on_next_clicked));
        this.$buttons.find(".of_planning_button_day").click(
            this.proxy(self.on_scale_day_clicked));
        this.$buttons.find(".of_planning_button_week").click(
            this.proxy(self.on_scale_week_clicked));
        this.$buttons.find(".of_planning_button_month").click(
            this.proxy(self.on_scale_month_clicked));

        this.$buttons.find('.of_planning_button_scale_' + this.mode).toggleClass("btn-primary btn-default");
        
        if ($node) {
            this.$buttons.appendTo($node);
        } else {
            this.$('.of_planning_buttons').replaceWith(this.$buttons);
        }
    },/**/
    /**
     *  mode switching
     */
    on_prev_clicked: function (ev) {
        console.log("on_prev_clicked!",ev);
        this.range_stop = moment(this.range_start).subtract(1, 'hours').endOf(this.mode)._d;
        this.range_start = moment(this.range_start).subtract(1, 'hours').startOf(this.mode)._d;
        console.log("le moment: ",)
        this.$small_calendar.datepicker("setDate",moment(this.range_start).format("MM/DD/YYYY"));
        this.do_search(this.domain,this.context,this.group_by);
    },
    on_today_clicked: function(ev) {
        console.log("on_today_clicked!",ev);
        this.range_start = moment().startOf(this.mode)._d;
        this.range_stop = moment().endOf(this.mode)._d;
        this.$small_calendar.datepicker("setDate",moment().format("MM/DD/YYYY"));
        this.do_search(this.domain,this.context,this.group_by);
    },
    on_next_clicked: function (ev) {
        console.log("on_next_clicked!",ev);
        this.range_start = moment(this.range_stop).add(1, 'hours').startOf(this.mode)._d;
        this.range_stop = moment(this.range_stop).add(1, 'hours').endOf(this.mode)._d;
        this.$small_calendar.datepicker("setDate",moment(this.range_start).format("MM/DD/YYYY"));
        this.do_search(this.domain,this.context,this.group_by);
    },
    on_scale_day_clicked: function(ev) {
        console.log("on_scale_day_clicked!",ev);
        if (this.mode != "day") {
            this.$buttons.find('.of_planning_button_' + this.mode).toggleClass("btn-primary btn-default");
            this.$buttons.find('.of_planning_button_day').toggleClass("btn-primary btn-default");
            this.do_switch_mode("day");
        }
    },
    on_scale_week_clicked: function(ev) {
        console.log("on_scale_week_clicked!",ev);
        if (this.mode != "week") {
            this.$buttons.find('.of_planning_button_' + this.mode).toggleClass("btn-primary btn-default");
            this.$buttons.find('.of_planning_button_week').toggleClass("btn-primary btn-default");
            this.do_switch_mode("week");
        }
    },
    on_scale_month_clicked: function(ev) {
        console.log("on_scale_month_clicked!",ev);
        if (this.mode != "month") {
            this.$buttons.find('.of_planning_button_' + this.mode).toggleClass("btn-primary btn-default");
            this.$buttons.find('.of_planning_button_month').toggleClass("btn-primary btn-default");
            this.do_switch_mode("month");
        }
    },
    do_switch_mode: function(new_mode) {
        console.log("do_switch_mode: ",this.mode,new_mode);
        this.mode = new_mode;
        this.column_nb = MODE_COLUMN_NBS[this.mode];
        this.range_start = moment().startOf(this.mode)._d;
        this.range_stop = moment().endOf(this.mode)._d;
        //this.do_search(this.domain,this.context,this.group_by);
    },
    on_all_rows_rendered: function() {
        console.log("all rows rendered!")
        if (this.sidebar) {
            if (this.sidebar.info_filter.rendered) {
                console.log("ALREADY RENDERED!");
                this.sidebar.info_filter.apply_filters();
            }else{
                this.sidebar.info_filter.render();
            }
        }
    },

    set_columns: function() {
        switch (this.mode) {
            case "week": return this.set_columns_week();
        };
    },
    set_columns_week: function() {
        this.head_column = {
            "text": "S" + moment(this.range_start).add(1, 'days').week(),
            "type": "resource_info",
        };
        var res = [];
        var jours = ["Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim."];
        var le_text, la_date, le_dict = {};
        for (var i=0; i<this.column_nb; i++) {
            le_text = jours[i] + " " + moment(this.range_start).add(i, 'days').format('L');
            la_date = moment(this.range_start).add(i, 'days')._d;
            le_dict = {
                "text": le_text,
                "date": la_date,
                "type": "date",
            }
            res.push(le_dict);
        }
        this.columns = res;
        if (!isNullOrUndef(this.table)) {
            this.table.head_column = this.head_column;
            this.table.columns = this.columns;
        }
        return res;
    },

    /**
     * Build OpenERP Domain to filter object by this.date_start field
     * between given start, end dates.
     */
    get_range_domain: function(domain, start, end) {
        var format = time.datetime_to_str;
        var extend_domain = [[this.date_start, '<=', format(end)]];
        if (this.date_stop) {
            extend_domain.push([this.date_stop, '>=', format(start)]);
        } else if (!this.date_delay) {
            extend_domain.push([this.date_start, '>=', format(start)]);
        }
        return new CompoundDomain(domain, extend_domain);
    },
});

PlanningView.Table = Widget.extend({
    template: "PlanningView.table",
    custom_events: {
        'row_rendered': 'on_row_rendered',
    },
    init: function(parent, options) {
        console.log("PlanningView.Table init args: ",arguments);
        this._super.apply(this, arguments);
        this.view = parent;
        this.columns = this.view.columns;
        this.head_column = this.view.head_column;
        this.rows = this.view.rows;
        this.appendTo(this.view.$table_container);
        //this.willStart();
    },
    /**
     *
     */
     willStart: function () {
        console.log("WILLSTART PlanningView.Table");
        return $.when();
        /*var self = this;
        var rendered_prom = this.$el.html(qweb.render(this.template, this)).promise();
        return $.when(rendered_prom,this._super())
            .then(function() {
                return self.$el.appendTo(self.view.$table);
            })
            .then(self.start());*/
    },
    /**
     *
     */
    start: function () {
        console.log("START PlanningView.Table");
        this.$tbody = this.$("tbody");
        console.log("TBODY LEN:",this.$tbody.length);
        return this._super();
    },
    renderElement: function() {
        var $el;
        if (this.template) {
            $el = $(qweb.render(this.template, {table: this}).trim());
        } else {
            $el = this._make_descriptive();
        }
        this.replaceElement($el);
    },
    on_row_rendered: function() {
        console.log("on row rendered");
        if (this.check_all_rows_rendered()) {
            this.trigger_up("all_rows_rendered");
        }
    },
    check_all_rows_rendered: function() {
        for (var k in this.rows) {
            if (!this.rows[k].rendered) {
                return false;
            }
        }
        return true;
    },
});

PlanningView.Row = Widget.extend({
    template: "PlanningView.row",
    tagName: 'tr',
    init: function(parent, view, records, options) {
        console.log("PlanningView.Row init args: ",arguments);
        this._super.apply(this, arguments);
        this.options = options;
        this.color_bg = options.color_bg;
        var le_rgb = hexToRgb(this.color_bg);
        this.color_bg_rgba = "rgba(" + le_rgb.r + "," + le_rgb.g + "," + le_rgb.b + ",0.3);"
        this.color_ft = options.color_ft;
        this.res_id = options.res_id;
        this.id = "of_planning_row_" + this.res_id;
        this.hidden = options.hidden || false;
        this.table = view.table;
        this.view = view;
        this.head_column = this.options.head_column;
        this.column_nb = this.view.column_nb;
        this.columns = new Array(this.column_nb);
        this.fillerbars = [];//new Array(this.column_nb);
        this.records_multiples = {};
        for (var i=0; i<this.columns.length; i++) {
            this.columns[i] = [];
        }
        this.assing_records_to_columns(records);
        //this.willStart();
    },
    /**
     *
     */
     willStart: function () {
        console.log("WILLSTART PlanningView.Row");
        var self = this;
        var rendered_prom;
        

        return $.when(rendered_prom,this._super())
            /*.then(function() {
                return self.$el.appendTo(self.table.$tbody);
            })
            .then(self.start())*/;
    },
    /**
     *
     */
    start: function () {
        console.log("START PlanningView.Row");
        this.$el.attr("id", this.id);
        //this.$el.css("background-color", this.color_bg);
        //this.$el.css("opacity", 0.3);
        return this._super();
    },
    /**
     *
     */
    render: function () {
        var self = this;

        var le_model = new Model("of.planning.intervention");
        var fillerbars = {};
        //console.log("self.res_id",self.res_id);
        fillerbars = le_model.call("get_fillerbar_data",[self.res_id, self.view.range_start, self.view.range_stop]).promise();
        //$.when(fillerbars).then(function(res){fillerbars = res;console.log("FILLERBARS!",fillerbars);});


        var $la_row = self.table.$('#'+self.id);
        if ($la_row.length >0) {
            console.log("FOUND",self.$el);
            return self.replace($la_row);
        }
        //console.log("NOT FOUND, TBODY",self.table.$tbody);
        return $.when(fillerbars)
            .then(function(res){
                self.horaires = res["horaires"];
                self.duree_journee = self.horaires[1] - self.horaires[0] + self.horaires[3] - self.horaires[2]
                if (self.duree_journee <= 0) {
                    throw new Error(_t("length of a working day must be superior to 0"));
                }
                self.fillerbars_dump = res;
                self.fillerbars = [];
                function get_time_total (horaires, interv_array) {
                    var le_time = 0;
                    for (var i=0; i<interv_array.length; i++) {
                        le_time += interv_array[i][1] - interv_array[i][0];
                        if (horaires[1] >= interv_array[i][0] && horaires[2] <= interv_array[i][1]) {  // chevauchement pause midi
                            le_time -= (horaires[2] - horaires[1]);
                        }
                    }
                    return le_time;
                }
                
                var a_push;
                for (var j=0; j<res["interventions"].length; j++) {
                    a_push = {"total": self.duree_journee, "occupe": get_time_total(res["horaires"],res["interventions"][j])};
                    a_push["pct_occupe"] = a_push["occupe"] * 100 / a_push["total"];
                    a_push["disponible"] = a_push["total"] - a_push["occupe"]
                    self.fillerbars.push(a_push)//[j] = new PlanningFillerBar(self, j, a_push, self.view);
                }
                console.log("fillerbars DUMP!",self.fillerbars_dump);
                console.log("self.FILLERBARS!",self.fillerbars);
                return $.when();
            })
            .then(function() {return self.$el.html(qweb.render(self.template, {"row": self})).promise()})
            .then(function (){
                //console.log("self.$el:",self.$el);
                for (var i=0; i<self.fillerbars.length; i++) {
                    //self.fillerbars[i].render();
                }
                self.$el.attr("id", self.id);
                self.rendered = true;
                //self.$el.css("background-color", self.color_bg);
                //self.$el.css("opacity", 0.3);
                //self.$("td").css("opacity", 1);
                self.$el.appendTo("tbody.of_planning_table_tbody");
                if (self.hidden) {
                    self.do_hide();
                }
                self.trigger_up("row_rendered")
                /* record multiples
                var $le_svg = $("svg");
                console.log("LE SVG",$le_svg);
                function connect_divs (div1, div2) {
                    var $div1 = $(div1);
                    var $div2 = $(div2);
                    var pos1 = $div1.position();
                    var pos2 = $div2.position();
                    console.log("pos1:",pos1);
                    console.log("pos2:",pos2);
                    var a_add = "<svg><line x1='"+pos1.left+"' y1='"+pos1.top+"' x2='"+pos2.left+"' y2='"+pos2.top+"'></svg>"
                    $(".of_planning_container").append(a_add);
                }
                for (var le_id in self.records_multiples) {
                    var $records_multiples = self.$(".of_planning_record_"+le_id);
                    console.log("$records_multiples",$records_multiples);
                    if (!$records_multiples.length) {
                        console.log("CEST UN ECHEC");
                        continue;
                    }
                    var record_prec;// = $records_multiples[0];
                    var record_curr;
                    for (var i=1; i<$records_multiples.length; i++) {
                        record_prec = $records_multiples[i-1];
                        record_curr = $records_multiples[i];
                        connect_divs(record_prec, record_curr);
                    }
                }


                /*var $records_multiples = self.$(".of_planning_record_multiple");
                if ($records_multiples.length > 0) {
                    console.log("$records_multiples",$records_multiples);
                    var le_res;
                    for (var i=0; i<$records_multiples.length; i++) {
                        console.log("elem?:", $records_multiples[i]);
                    }
                    var $records_multiples_grouped;
                }*/
                
            });

    },
    renderElement: function() {
        var $el;
        if (this.template) {
            $el = $(qweb.render(this.template, {row: this}).trim());
        } else {
            $el = this._make_descriptive();
        }
        this.replaceElement($el);
    },
    /**
     *
     */
    add_record: function (planning_record) {
        if (!planning_record.col_offset_start) {
            console.log("ERREUR: col_offset_start manquant",record);
        }else if(isNullOrUndef(planning_record.col_offset_stop)) {  // 1 day event
            this.columns[planning_record.col_offset_start].push(planning_record);
        }else{  // several days event
            //console.log("PLANNING RECORD SEVDAYS:",planning_record);
            this.records_multiples[planning_record.id] = [];
            for (var i=planning_record.col_offset_start; i<=planning_record.col_offset_stop; i++) {
                if (i>=0 && i<this.column_nb) {
                    console.log("pushed to column ",i);
                    this.columns[i].push(planning_record);
                    this.records_multiples[planning_record.id].push(i);
                }
            }
        }
    },
    /**
     *
     */
    assing_records_to_columns: function (planning_records) {
        if (isNullOrUndef(planning_records)) {
            console.log("planning_records is ",planning_record);
            return false;
        }
        var planning_record;
        for (var i=0; i<planning_records.length; i++) {
            planning_record = planning_records[i];
            this.add_record(planning_record);
        }
    },
});

var PlanningFillerBar = Widget.extend({
    template: 'PlanningView.fillerbar',
    init: function(row, column, fillerbar_data, view) {
        this._super.apply(this, arguments);
        this.row = row;
        this.res_id = row.res_id;
        this.column = column;
        this.fillerbar_data = fillerbar_data;
        this.view = view;
    },
    render: function() {
        var $la_div = $("#of_planning_fillerbar_" + this.res_id + "_" + this.column);
        if ($la_div.length > 0) {
            console.log("TROUVÉ",$la_div);
        }else{
            console.log("pas trouvé...")
        }
    },
});

var PlanningRecord = Widget.extend({
    /**
     *
     */
    template: 'PlanningView.record',
    events: {
        //'click .of_map_record_action': 'on_map_record_action_clicked',
        //'click .of_map_record_close': 'on_map_record_close_clicked',
    },
    /**
     *  Inits map_record
     */
    init: function(view, record, options) {
        //console.log('MapRecord.init arguments: ',arguments);
        this.id = record.id;
        this._super(view);
        this.view = view;
        this.options = options;
        this.color_bg = options.color_bg;
        this.color_ft = options.color_ft;
        this.day_span = options.day_span;
        if (this.day_span > 1) this.$els = [];
        this.class ="of_planning_record of_planning_record_" + this.id;
        if (this.day_span > 1) this.class += " of_planning_record_multiple";
        this.col_offset_start = options.col_offset_start;
        this.col_offset_stop = options.col_offset_stop;
        this.read_only_mode = options.read_only_mode || true; // current implementation solo readonly

        this.minimized = false;
        this.diplayable_content = {};

        this.date_start = record[this.view.date_start];
        this.date_stop = record[this.view.date_stop];

        var self= this;
        this.init_content(record);
        //console.log('MapRecord this: ',this);
    },
    /**
     *  inits this.values ({fieldName: value, ...}),
     */
    init_content: function (record) {
        var self = this;
        this.values = {};
        _.each(record, function(v, k) {
            self.values[k] = {
                value: v.value
            };
        });
        this.record = record;
        var descript_dt = {type: "datetime"};
        var descript_ft = {type: "float_time"};
        var formatted_date = formats.format_value(record.date,descript_dt).substring(11, 16);
        var formatted_date_deadline = formats.format_value(record.date_deadline,descript_dt).substring(11, 16);
        var formatted_duree = formats.format_value(record.duree,descript_ft).replace(":", "h");
        this.content = "" +
        "<div class='" + this.class + "' " +
            "style='color: " + this.color_ft + "; background-color: " + this.color_bg +
            "; padding: 2px 8px 4px; border-radius: 4px; border: 1px solid " + this.color_ft + ";'>" +
            "<div class='of_planning_info of_planning_info_heures'>" +
                "<i class='fa fa-clock-o'/>&nbsp;" +
                "<span class='of_planning_subinfo of_planning_subinfo_heure_debut'>" + formatted_date + "</span>" +
                "<span class='of_planning_subinfo of_planning_subinfo_heure_fin'> -> </span>" +
                "<span class='of_planning_subinfo of_planning_subinfo_heure_fin'>" + formatted_date_deadline + "</span>" +
                "<span class='of_planning_subinfo of_planning_subinfo_duree'> - </span>" +
                "<span class='of_planning_subinfo of_planning_subinfo_duree'>" + formatted_duree + "</span>" +
            "</div>" +
            "<div class='of_planning_info of_planning_info_tache_name'><i class='fa fa-cogs'/>&nbsp;" + record.tache_name + "</div>" 
        if (record.partner_name) {
            this.content += "<div class='of_planning_info of_planning_info_partner_name'><i class='fa fa-user'/>&nbsp;" + record.partner_name + "</div>"
        }
        this.content += "<div class='of_planning_info of_planning_info_lieu'>"
        if (record.address_zip || record.address_city) {
            this.content += "<i class='fa fa-map-marker'/>&nbsp;"
        }
        if (record.address_zip) {
            this.content += "<span class='of_planning_subinfo of_planning_subinfo_zip'>" + record.address_zip + "</span>"
        }
        if (record.address_city) {
            this.content += "&nbsp;<span class='of_planning_subinfo of_planning_subinfo_city'>" + record.address_city + "</span>"
        }
        this.content += "" +
            "</div>" +
        "</div>"
        //console.log("planning_record this: ",this);
    },
    /**
     *
     */
    start: function () {
        console.log("START PlanningRecord");;
        return this._super();
    },
});

PlanningView.Sidebar = Widget.extend({
    template: 'PlanningView.sidebar',
    
    start: function() {
        this.reso_filter = new PlanningView.SidebarResoFilter(this, this.getParent());
        this.info_filter = new PlanningView.SidebarInfoFilter(this, this.getParent());
        return $.when(this._super(), this.reso_filter.appendTo(this.$el), this.info_filter.appendTo(this.$el));
    }
});
PlanningView.SidebarResoFilter = Widget.extend({
    events: {
        'click .of_planning_contacts': 'on_click',
    },
    template: 'PlanningView.sidebar.reso_filters',

    init: function(parent, view) {
        this._super(parent);
        this.view = view;
    },
    render: function() {
        var self = this;

        var fil = self.view.get_all_filters_ordered()
        //async
        $.when(fil).then(function(){ // fil is a promise
            var filters = _.filter(fil.target, function(filter) {
                return _.contains(self.view.now_filter_ids, filter.value);
            });
            console.log("filters",filters);
            self.$('.of_planning_contacts').html(qweb.render('PlanningView.sidebar.contacts', { filters: filters }));
        });
    },
    on_click: function(e) {
        console.log("CLICK");
        if (e.target.tagName == 'SPAN') {  // click sur span -> la checkboxe est a coté
            var la_input = e.target.previousElementSibling.firstElementChild;
            $("#"+la_input.id).click();
            return;
        }
        if (e.target.tagName == 'DIV') {
            $(e.target).find('input').click();
            return;
        }
        this.view.all_filters[e.target.value].is_checked = e.target.checked;
        var row_id = "of_planning_row_"+e.target.value;
        var la_row = this.view.rows[e.target.value];
        la_row.hidden = !e.target.checked;
        la_row.do_toggle(e.target.checked);
        //console.log("LA ROW",la_row);
        //this.trigger_up('reload_events');
    },
});

PlanningView.SidebarInfoFilter = Widget.extend({
    events: {
        'click .of_planning_ev_infos': 'on_click',
        'click .of_planning_info_filter_show': 'on_click_show_filters',
        'click .of_planning_info_filter_hide': 'on_click_hide_filters',
    },
    template: 'PlanningView.sidebar.info_filters',

    init: function(parent, view) {
        var self = this;
        this._super(parent);
        this.view = view;
        this.info_filters_visible = (local_storage.getItem('planningview_info_filters_visible') == 'true');
        local_storage.setItem('planningview_info_filters_visible', this.info_filters_visible);
        //this.on_click = _.debounce(this.on_click, 300, true);
        $.when(this.init_filters()).then(function(){self.render()});
    },
    init_filters: function() {
        var self = this;

        var check_tab_names = ["client","tache","zip","city","heure_debut","heure_fin","duree"];
        var check_tab_vals = new Array(7);
        var check_tab_defs = new Array(7);
        var dfd = $.Deferred();
        var p = dfd.promise(self.info_filters);
        var defs = [], proms = [], les_args, le_def;
        var ir_values_model = new Model("ir.values");
        check_tab_defs[0] = ir_values_model.call("get_default", ["of.intervention.config.settings", "planningview_filter_" + check_tab_names[0], false]);
        $.when(check_tab_defs[0]).then(function(res){check_tab_vals[0] = isNullOrUndef(res) || res});
        check_tab_defs[1] = ir_values_model.call("get_default", ["of.intervention.config.settings", "planningview_filter_" + check_tab_names[1], false]);
        $.when(check_tab_defs[1]).then(function(res){check_tab_vals[1] = isNullOrUndef(res) || res});
        check_tab_defs[2] = ir_values_model.call("get_default", ["of.intervention.config.settings", "planningview_filter_" + check_tab_names[2], false]);
        $.when(check_tab_defs[2]).then(function(res){check_tab_vals[2] = isNullOrUndef(res) || res});
        check_tab_defs[3] = ir_values_model.call("get_default", ["of.intervention.config.settings", "planningview_filter_" + check_tab_names[3], false]);
        $.when(check_tab_defs[3]).then(function(res){check_tab_vals[3] = isNullOrUndef(res) || res});
        check_tab_defs[4] = ir_values_model.call("get_default", ["of.intervention.config.settings", "planningview_filter_" + check_tab_names[4], false]);
        $.when(check_tab_defs[4]).then(function(res){check_tab_vals[4] = isNullOrUndef(res) || res});
        check_tab_defs[5] = ir_values_model.call("get_default", ["of.intervention.config.settings", "planningview_filter_" + check_tab_names[5], false]);
        $.when(check_tab_defs[5]).then(function(res){check_tab_vals[5] = isNullOrUndef(res) || res});
        check_tab_defs[6] = ir_values_model.call("get_default", ["of.intervention.config.settings", "planningview_filter_" + check_tab_names[6], false]);
        $.when(check_tab_defs[6]).then(function(res){check_tab_vals[6] = isNullOrUndef(res) || res});

        $.when.apply($, check_tab_defs)
        //$.when(check_tab_defs[0],check_tab_defs[1],check_tab_defs[2],check_tab_defs[3],check_tab_defs[4],check_tab_defs[5],check_tab_defs[6])
        .then(function () {
            console.log("defs",defs);
            console.log("check_tab_defs",check_tab_defs);
            console.log("check_tab_vals",check_tab_vals);
            self.info_filters = {
                "client": {
                    "value": "client",
                    "input_id": "client_input",
                    "class": "of_planning_info_partner_name",
                    "label": "Client",
                    "is_checked": check_tab_vals[0],
                    "field_name_ir": "planningview_filter_client",
                },
                "tache": {
                    "value": "tache",
                    "input_id": "tache_input",
                    "class": "of_planning_info_tache_name",
                    "label": "Tache",
                    "is_checked": check_tab_vals[1],
                    "field_name_ir": "planningview_filter_tache",
                },
                "lieu": {
                    "value": "lieu",
                    "input_id": "lieu_input",
                    "class": "of_planning_info_lieu",
                    "label": "Lieu",
                    "is_checked": check_tab_vals[2] || check_tab_vals[3],
                    "child_filters_visible": (local_storage.getItem('planningview_info_filters_visible_lieu') == 'true'),
                    "child_filters": {
                        "zip": {
                            "value": "lieu-zip",
                            "input_id": "lieu-zip_input",
                            "class": "of_planning_subinfo_zip",
                            "label": "Code postal",
                            "is_checked": check_tab_vals[2],
                            "field_name_ir": "planningview_filter_zip",
                        },
                        "city": {
                            "value": "lieu-city",
                            "input_id": "lieu-city_input",
                            "class": "of_planning_subinfo_city",
                            "label": "Ville",
                            "is_checked": check_tab_vals[3],
                            "field_name_ir": "planningview_filter_city",
                        },
                    },
                },
                "heures": {
                    "value": "heures",
                    "input_id": "heures_input",
                    "class": "of_planning_info_heures",
                    "label": "Heures / Durées",
                    "is_checked": check_tab_vals[4] || check_tab_vals[5] || check_tab_vals[6],
                    "child_filters_visible": (local_storage.getItem('planningview_info_filters_visible_heures') == 'true'),
                    "child_filters": {
                        "heure_debut": {
                            "value": "heures-heure_debut",
                            "input_id": "heures-heure_debut_input",
                            "class": "of_planning_subinfo_heure_debut",
                            "label": "Heure de début",
                            "is_checked": check_tab_vals[4],
                            "field_name_ir": "planningview_filter_heure_debut",
                        },
                        "heure_fin": {
                            "value": "heures-heure_fin",
                            "input_id": "heures-heure_fin_input",
                            "class": "of_planning_subinfo_heure_fin",
                            "label": "Heure de fin",
                            "is_checked": check_tab_vals[5],
                            "field_name_ir": "planningview_filter_heure_fin",
                        },
                        "duree": {
                            "value": "heures-duree",
                            "input_id": "heures-duree_input",
                            "class": "of_planning_subinfo_duree",
                            "label": "Durée",
                            "is_checked": check_tab_vals[6],
                            "field_name_ir": "planningview_filter_duree",
                        },
                    },
                },
            }
            self.view.info_filters = self.info_filters;
            dfd.resolve();
        });

        return p;
    },
    render: function() {
        var self = this;
        console.log("info filters:",this.view.info_filters);

        $.when(self.$('.of_planning_ev_infos').html(qweb.render('PlanningView.sidebar.event_info', { filters: self.info_filters })))
        .then(function() {
            self.rendered = true;
            self.apply_filters();
            if (self.info_filters_visible == 'true' || self.info_filters_visible) {
                self.$('.of_planning_ev_infos').removeClass("o_hidden");
                self.$(".of_planning_info_filter_show").addClass("o_hidden");
                self.$(".of_planning_info_filter_hide").removeClass("o_hidden");
                for (var f in self.info_filters) {
                    if (!isNullOrUndef(self.info_filters[f].child_filters) && self.info_filters[f].child_filters_visible) {
                        $(".of_planning_ev_info_toggle_" + f).toggleClass("o_hidden");  // toggle arrow down/up
                        $(".of_planning_ev_subinfo_" + f).removeClass("o_hidden");  // toggle child_filters visible
                    }
                }
            }
        });

    },
    apply_filters: function () {
        for (var f in this.info_filters) {
            console.log("FFFFFF",f);
            var le_filter = this.info_filters[f], le_sub;
            var la_class = le_filter.class;
            if (le_filter.is_checked) {  // update event display
                $("."+la_class).removeClass("o_hidden");
            }else{
                //console.log(la_class,$("."+la_class));
                $("."+la_class).addClass("o_hidden");
            }
            for (var sub in le_filter.child_filters) {
                le_sub = le_filter["child_filters"][sub];
                la_class = le_sub.class;
                if (le_sub.is_checked) {  // update event display
                    $("."+la_class).removeClass("o_hidden");
                }else{
                    $("."+la_class).addClass("o_hidden");
                }
            }
        }
    },
    do_toggle_checked: function (checked, filter_value, rebounce=false) {
        var le_filter, le_parent, la_class, la_input_sel;
        var ir_values_model = new Model('ir.values');

        if ( filter_value instanceof Array) {
            le_parent = this.info_filters[filter_value[0]];
            le_filter = le_parent["child_filters"][filter_value[1]];
            
            if (rebounce) {
                if (checked && !le_parent.is_checked) {  // check parent filter if at least one of the subfilters is checked
                    this.do_toggle_checked(true,filter_value[0],false);
                }else if (this.all_subfilters_unchecked(filter_value[0]) && le_parent.is_checked) {  // uncheck parent filter if none of the subfilters is checked
                    this.do_toggle_checked(false,filter_value[0],false);
                }
            }
        }else{
            le_filter = this.info_filters[filter_value];

            if (rebounce && !isNullOrUndef(this.info_filters[filter_value].child_filters)) {  // filter has child filters: apply toggle to subfilters if rebounce=true
                var le_tab = [];
                for (var k in le_filter.child_filters) {
                    le_tab = [filter_value, k];
                    console.log("LE_TAB",le_tab);
                    this.do_toggle_checked(checked, le_tab, false);
                }
            }
            
        }
        le_filter.is_checked = checked;  // update data
        la_class = le_filter.class;
        la_input_sel = "#"+le_filter.input_id;
        if (!isNullOrUndef(le_filter["field_name_ir"])) { // update config settings
            ir_values_model.call("set_default", ["of.intervention.config.settings", le_filter["field_name_ir"], checked, false]);
        }
        if (checked != $(la_input_sel).prop("checked")) { // update filter display
            $(la_input_sel).prop("checked", checked);
        }
        if (checked) {  // update event display
            $("."+la_class).removeClass("o_hidden");
        }else{
            $("."+la_class).addClass("o_hidden");
        }
        //console.log("le_filter['field_name_ir']",le_filter["field_name_ir"]);
        //console.log("le_filter",le_filter);
        
    },
    all_subfilters_unchecked: function (filter_value) {
        for (var k in this.info_filters[filter_value]["child_filters"]) {
            if (this.info_filters[filter_value]["child_filters"][k].is_checked) {
                return false;
            }
        }
        return true;
    },
    on_click: function(e) {
        console.log("CLICK",e.target.tagName);
        //console.log("event target:",e.target);
        var la_value = e.target.value;
        var la_class;
        if (e.target.tagName == 'SPAN') {  // click sur span -> la checkboxe est a coté
            var la_input = e.target.previousElementSibling.firstElementChild;
            $("#"+la_input.id).click();
            return;
        }
        if (e.target.tagName == 'DIV') {  // click sur div
            if (e.target.className == "of_planning_ev_info" || e.target.className.indexOf("of_planning_ev_subinfo") != -1) {  // click sur div du filtre TODO className.indexOf
                $(e.target).find('input.' + e.target.className + '_input').click();
                console.log("CASE AA");
                return;
            }else{  // click sur div du widget
                console.log("CASE BB");
                return;
            }
        }
        if (e.target.tagName == 'I') {  // click sur i (montrer/cacher sous-filtres)
            //console.log(e);
            for (var i=0; i<e.target.classList.length; i++) {
                if (e.target.classList[i].indexOf("of_planning_ev_info_toggle") != -1) {
                    $("." + e.target.classList[i]).toggleClass("o_hidden");
                    break;
                }
            }
            la_value = e.target.id.split("_");
            if (la_value[1] == "show") {
                $(".of_planning_ev_subinfo_" + la_value[0]).removeClass("o_hidden");
                local_storage.setItem('planningview_info_filters_visible_' + la_value[0], true);
                //console.log("show",local_storage.getItem('planningview_info_filters_visible_'+la_value[0]));
            }else{
                $(".of_planning_ev_subinfo_" + la_value[0]).addClass("o_hidden");
                local_storage.setItem('planningview_info_filters_visible_' + la_value[0], false);
                //console.log("hide",local_storage.getItem('planningview_info_filters_visible_'+la_value[0]));
            }

            return;
        }
        var le_filter;
        if (la_value.indexOf("-") != -1) {
            la_value = la_value.split("-");
        }
        this.do_toggle_checked(e.target.checked, la_value, true);
    },
    on_click_show_filters: function(e) {
        //console.log("on_click_show_filters",e);
        this.$(".of_planning_info_filter_show").addClass("o_hidden");
        this.$(".of_planning_info_filter_hide").removeClass("o_hidden");
        this.do_toggle_filters(true);
    },
    on_click_hide_filters: function(e) {
        //console.log("on_click_hide_filters",e);
        this.$(".of_planning_info_filter_hide").addClass("o_hidden");
        this.$(".of_planning_info_filter_show").removeClass("o_hidden");
        this.do_toggle_filters(false);
    },
    do_toggle_filters: function(show) {
        if (show) {
            self.$('.of_planning_ev_infos').removeClass("o_hidden");
            this.info_filters_visible = true;
            local_storage.setItem('planningview_info_filters_visible', this.info_filters_visible);
        }else{
            self.$('.of_planning_ev_infos').addClass("o_hidden");
            this.info_filters_visible = false;
            local_storage.setItem('planningview_info_filters_visible', this.info_filters_visible);
        }
    },
});

core.view_registry.add('planning', PlanningView);

return PlanningView;
});