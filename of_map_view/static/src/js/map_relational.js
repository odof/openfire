odoo.define('of_map_view.Many2ManyMapView', function (require) {
"use strict";

var common = require('web.form_common');
var core = require('web.core');
var data = require('web.data');
var MapView = require('of_map_view.MapView');
var form_relational = require('web.form_relational');

var FieldOne2Many = core.form_widget_registry.get('one2many');
var FieldMany2Many = core.form_widget_registry.get('many2many');

var _t = core._t;

var X2ManyMapView = MapView.extend({
    /*render_pager: function($node, options) {
        options = _.extend(options || {}, {
            single_page_hidden: true,
        });
        this._super($node, options);
    },*/
    start: function() {
        console.log("test", this);
        var self = this
        var res = this._super();
        /*
            Si la map est dans un onglet qui n'est pas directement visible elle sera mal centrée.
            cela est dû au fait que leaflet pense que la map est de taille nulle.
            il faut donc vérifier que la map est dans un onglet et ajouter un listener sur le clique sur onglet
            même cas si la map commence à l'état invisible puis devient visible mais on traitera ça en temp voulu
        */
        if (this.$el.parent('div.o_notebook'.length)) {
            // la map est dans un onglet
            $(document)
            .on('click.bs.tab.data-api', '[data-toggle="tab"]', function(){
                console.log("oui?");
                if (self.$el.is(":visible")) {
                    // l'onglet est visible
                    self.map.the_map.invalidateSize();
                    self.map.set_bounds();
                }
            });
        }
        // à debugguer quand temp dispo
        this.on("change:effective_invisible", this, function() {
            console.log("HAHA");
            if (self.get("effective_invisible") === false) {
                self.map.the_map.invalidateSize();
                self.map.set_bounds();
                console.log("HOHO");
            }
        });

        return res
    },
});

var One2ManyMapView = X2ManyMapView.extend({
    /*add_record: function() {
        var self = this;
        new common.FormViewDialog(this, {
            res_model: self.x2m.field.relation,
            domain: self.x2m.build_domain(),
            context: self.x2m.build_context(),
            title: _t("Create: ") + self.x2m.string,
            initial_view: "form",
            alternative_form_view: self.x2m.field.views ? self.x2m.field.views.form : undefined,
            create_function: function(data, options) {
                return self.x2m.data_create(data, options);
            },
            read_function: function(ids, fields, options) {
                return self.x2m.data_read(ids, fields, options);
            },
            parent_view: self.x2m.view,
            child_name: self.x2m.name,
            form_view_options: {'not_interactible_on_create':true},
            on_selected: function() {
                self.x2m.reload_current_view();
            }
        }).open();
    },*/
});

var Many2ManyMapView = X2ManyMapView.extend({
    /*add_record: function() {
        var self = this;
        new common.SelectCreateDialog(this, {
            res_model: this.x2m.field.relation,
            domain: new data.CompoundDomain(this.x2m.build_domain(), ["!", ["id", "in", this.dataset.ids]]),
            context: this.x2m.build_context(),
            title: _t("Add: ") + this.x2m.string,
            on_selected: function(element_ids) {
                return self.x2m.data_link_multi(element_ids).then(function() {
                    self.x2m.reload_current_view();
                });
            }
        }).open();
    },
    open_record: function(event) {
        var self = this;
        new common.FormViewDialog(this, {
            res_model: this.x2m.field.relation,
            res_id: event.data.id,
            context: this.x2m.build_context(),
            title: _t("Open: ") + this.x2m.string,
            write_function: function(id, data, options) {
                return self.x2m.data_update(id, data, options).done(function() {
                    self.x2m.reload_current_view();
                });
            },
            alternative_form_view: this.x2m.field.views ? this.x2m.field.views.form : undefined,
            parent_view: this.x2m.view,
            child_name: this.x2m.name,
            read_function: function(ids, fields, options) {
                return self.x2m.data_read(ids, fields, options);
            },
            form_view_options: {'not_interactible_on_create': true},
            readonly: !this.is_action_enabled('edit') || this.x2m.get("effective_readonly")
        }).open();
    },*/
});

core.view_registry
    .add('one2many_map', One2ManyMapView)
    .add('many2many_map', Many2ManyMapView);

core.one2many_view_registry
    .add('map', One2ManyMapView);

FieldOne2Many.include({
    init: function() {
        this._super.apply(this, arguments);
        this.x2many_views = _.extend(this.x2many_views, {
            map: One2ManyMapView,
        });
    },
});

FieldMany2Many.include({
    init: function() {
        this._super.apply(this, arguments);
        this.x2many_views = _.extend(this.x2many_views, {
            map: Many2ManyMapView,
        });
    },
});

core.form_widget_registry
    .add('many2many_map', FieldMany2Many)
    .add('one2many_map', FieldOne2Many)

});

