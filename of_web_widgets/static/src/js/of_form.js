odoo.define('of_web_widgets.of_form', function (require) {
"use strict";

var form_common = require('web.form_common');
var form_widgets = require('web.form_widgets');
var form_relational = require('web.form_relational');
var utils = require('web.utils');
var core = require('web.core');
var data = require('web.data');
var Model = require('web.DataModel');
var Dialog = require('web.Dialog');
var ViewManager = require('web.ViewManager');
var ControlPanel = require('web.ControlPanel');

var FieldMany2One = form_relational.FieldMany2One;
var FieldOne2Many = core.form_widget_registry.get('one2many');

var _t = core._t;

form_common.CompletionFieldMixin.init = function(){
    this.limit = 7;
    this.orderer = new utils.DropMisordered();
    this.can_create = this.node.attrs.can_write == "false" ? false : true;
    this.can_write = this.node.attrs.can_write == "false" ? false : true;
    this.options.no_quick_create = true;
};

/**
 *  Empecher le multi-click
 */
form_widgets.WidgetButton.include({
    willStart: function() {
        this.on_click = _.debounce(this.on_click, 300, true);
        this.on_confirmed = _.debounce(this.on_confirmed, 300, true);
        return $.when(this._super.apply(this, arguments));
    },
})

/**
 *  Copy from form_relational_widget for FieldOne2Many.load_views
 */
var X2ManyViewManager = ViewManager.extend({
    custom_events: {
        // Catch event scrollTo to prevent scrolling to the top when using the
        // pager of List and Kanban views in One2Many fields
        'scrollTo': function() {},
    },
    init: function(parent, dataset, views, flags, x2many_views) {
        // By default, render buttons and pager in X2M fields, but no sidebar
        flags = _.extend({}, flags, {
            headless: false,
            search_view: false,
            action_buttons: true,
            pager: true,
            sidebar: false,
        });
        this.control_panel = new ControlPanel(parent, "X2ManyControlPanel");
        this.set_cp_bus(this.control_panel.get_bus());
        this._super(parent, dataset, views, flags);
        this.registry = core.view_registry.extend(x2many_views);
    },
    start: function() {
        this.control_panel.prependTo(this.$el);
        return this._super();
    },
    switch_mode: function(mode, unused) {
        if (mode !== 'form') {
            return this._super(mode, unused);
        }
        var self = this;
        var id = self.x2m.dataset.index !== null ? self.x2m.dataset.ids[self.x2m.dataset.index] : null;
        var pop = new form_common.FormViewDialog(this, {
            res_model: self.x2m.field.relation,
            res_id: id,
            context: self.x2m.build_context(),
            title: _t("Open: ") + self.x2m.string,
            create_function: function(data, options) {
                return self.x2m.data_create(data, options);
            },
            write_function: function(id, data, options) {
                return self.x2m.data_update(id, data, options).done(function() {
                    self.x2m.reload_current_view();
                });
            },
            alternative_form_view: self.x2m.field.views ? self.x2m.field.views.form : undefined,
            parent_view: self.x2m.view,
            child_name: self.x2m.name,
            read_function: function(ids, fields, options) {
                return self.x2m.data_read(ids, fields, options);
            },
            form_view_options: {'not_interactible_on_create':true},
            readonly: self.x2m.get("effective_readonly")
        }).open();
        pop.on("elements_selected", self, function() {
            self.x2m.reload_current_view();
        });
    },
});

FieldOne2Many.include({
    /**
     *  Override copy of parent function. Adds calendar and map views to possible O2M views
     */
    load_views: function() {
        var self = this;

        var view_types = this.node.attrs.mode;
        view_types = !!view_types ? view_types.split(",") : [this.default_view];
        var views = [];
        _.each(view_types, function(view_type) {
            if (! _.include(["list", "tree", "graph", "kanban", "calendar", "map"], view_type)) { // NEW: add calendar and map to possible views
                throw new Error(_.str.sprintf(_t("View type '%s' is not supported in X2Many."), view_type));
            }
            var view = {
                view_id: false,
                view_type: view_type === "tree" ? "list" : view_type,
                fields_view: self.field.views && self.field.views[view_type],
                options: {},
            };
            if(view.view_type === "list") {
                _.extend(view.options, {
                    action_buttons: false, // to avoid 'Save' and 'Discard' buttons to appear in X2M fields
                    addable: null,
                    selectable: self.multi_selection,
                    sortable: true,
                    import_enabled: false,
                    deletable: true
                });
                if (self.get("effective_readonly")) {
                    _.extend(view.options, {
                        deletable: null,
                        reorderable: false,
                    });
                }
            } else if (view.view_type === "kanban") {
                _.extend(view.options, {
                    action_buttons: true,
                    confirm_on_delete: false,
                });
                if (self.get("effective_readonly")) {
                    _.extend(view.options, {
                        action_buttons: false,
                        quick_creatable: false,
                        creatable: false,
                        read_only_mode: true,
                    });
                }
            }
            views.push(view);
        });
        this.views = views;

        this.viewmanager = new X2ManyViewManager(this, this.dataset, views, this.view_options, this.x2many_views);
        this.viewmanager.x2m = self;
        var def = $.Deferred().done(function() {
            self.initial_is_loaded.resolve();
        });
        this.viewmanager.on("controller_inited", self, function(view_type, controller) {
            controller.x2m = self;
            if (view_type == "list") {
                if (self.get("effective_readonly")) {
                    controller.on('edit:before', self, function (e) {
                        e.cancel = true;
                    });
                    _(controller.columns).find(function (column) {
                        if (!(column instanceof list_widget_registry.get('field.handle'))) {
                            return false;
                        }
                        column.modifiers.invisible = true;
                        return true;
                    });
                }
            } else if (view_type == "graph") {
                self.reload_current_view();
            }
            def.resolve();
        });
        this.viewmanager.on("switch_mode", self, function(n_mode) {
            $.when(self.commit_value()).done(function() {
                if (n_mode === "list") {
                    utils.async_when().done(function() {
                        self.reload_current_view();
                    });
                }
            });
        });
        utils.async_when().done(function () {
            self.$el.addClass('o_view_manager_content');
            self.alive(self.viewmanager.attachTo(self.$el));
        });
        return def;
    },
});

/**
 *  Field to somehow emulate the behavior of 1-1 connections
 *  Mostly works like a Many2one
 *  no value displayed: either Create or See
 *  no dropdown menu
 *  only a button that will open a pop up in "view", "create" and "edit" mode
 */
var FieldOne2One = FieldMany2One.extend({
    template: "FieldOne2One",

    init: function(field_manager, node) {
        this._super.apply(this, arguments);
        //console.log("FieldOne2One init this and arguments: ",this,arguments);

    },

    initialize_content: function() {  // override -> no call to parent function render_editable
        this.render_init();
    },

    render_init: function() {  // formerly render_editable()
        var self = this;

        if (!this.get("value")) {  // no value yet -> offer to create a record
            this.$el.click(function(ev) {
                ev.preventDefault();
                var context = self.build_context().eval();
                var model_obj = new Model(self.field.relation);
                model_obj.call('get_formview_id', [[self.get("value")], context]).then(function(view_id){
                    var pop = new form_common.FormViewDialog(self, {
                        res_model: self.field.relation,
                        res_id: self.get("value"),
                        context: self.build_context(),
                        title: _t("Create: ") + self.string,
                        view_id: view_id,
                        readonly: self.get('effective_readonly'),
                        disable_multiple_selection: true,  // disable button "save & new"
                    }).open();
                    pop.on('create_completed', self, function(new_id){
                        self.set("value", new_id);
                        var new_value = {}
                        new_value["" + this.get("value")] = this.get("value");
                        self.display_value = new_value;
                        self.display_value_backup = new_value;
                        self.render_value();
                        self.focus();
                        self.trigger('changed_value');
                    });
                    pop.on('record_saved', self, function(){  //
                        self.display_value = {};
                        self.display_value_backup = {};
                        self.render_value();
                        self.focus();
                        self.trigger('changed_value');
                    });
                });
            });
        }else{
            this.$el.click(function(ev) {
                ev.preventDefault();
                var context = self.build_context().eval();
                var model_obj = new Model(self.field.relation);
                model_obj.call('get_formview_id', [[self.get("value")], context]).then(function(view_id){
                    var pop = new form_common.FormViewDialog(self, {
                        res_model: self.field.relation,
                        res_id: self.get("value"),
                        context: self.build_context(),
                        title: _t("Open: ") + self.string,
                        view_id: view_id,
                        readonly: self.get('effective_readonly'),
                    }).open();
                    pop.on('record_saved', self, function(){
                        self.display_value = {};
                        self.display_value_backup = {};
                        self.render_value();
                        self.focus();
                        self.trigger('changed_value');
                        //console.log("record_saved B self: ",self);
                    });
                });
            });
        };

        this.setupFocus(this.$el);
    },

    display_string: function (str) {
        var noValue = (str === null);
        var text_empty = this.options.text_empty || _t("Create: ") + this.field.string;//_t(this.field.string);
        var text_nonempty = this.options.text_nonempty || _t("See: ") + _t(this.field.string);
        this.$el.html(noValue ? text_empty : text_nonempty || data.noDisplayContent);
    },
});

core.form_widget_registry
    .add('one2one', FieldOne2One);

return FieldOne2One;

});
