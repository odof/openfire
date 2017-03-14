odoo.define('of_map_view.MapView', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Model = require('web.DataModel');
var View = require('web.View');
var Pager = require('web.Pager');
var pyeval = require('web.pyeval');
var session = require('web.session');
var utils = require('web.utils');
var ActionManager = require('web.ActionManager');
var map_controls = require('of_map_view.map_controls');
var Widget = require('web.Widget');
var mixins = core.mixins;

//var TILE_SERVER_ADDR = 'http://192.168.1.80/osm_tiles/{z}/{x}/{y}.png';
var TILE_SERVER_ADDR = '//{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png';

var Class = core.Class;
var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

var MapView = View.extend({
    template: 'MapView',
    display_name: _lt('Map'),
    icon: 'fa fa-map-marker',
    view_type: "map",
    className: "o_map_view",
    _model: null,
    defaults: _.extend({}, View.prototype.defaults, {
        // records can be selected one by one
        selectable: true,
        // list rows can be deleted
        deletable: false,
        // whether the column headers should be displayed
        header: true,
        // display addition button, with that label
        addable: _lt("Create"),
        // whether the list view can be sorted, note that once a view has been
        // sorted it can not be reordered anymore
        sortable: true,
        // whether the view rows can be reordered (via vertical drag & drop)
        reorderable: true,
        action_buttons: true,
        // whether the editable property of the view has to be disabled
        disable_editable_mode: false,
        auto_search: false, // the search is done when the map is attached. See MapView.Map.on_map_attached. Apparently not taken into account D:
        dummy_option: 'dummy_string' // for testing
    }),
    custom_events: {
        'map_record_open': 'open_record',
    },
    /**
     *
     */
    init: function() {
        //console.log("MapView.init: ",arguments);
        this._super.apply(this, arguments);

        this._model = new Model(this.dataset.model);
        this.name = "" + this.fields_view.arch.attrs.string;

        // the view's number of records per page (|| section), defaults to 80
        this._limit = (this.options.limit ||
                       this.defaults.limit ||
                       (this.getParent().action || {}).limit ||
                       parseInt(this.fields_view.arch.attrs.limit, 10) ||
                       80);
        // the index of the first displayed record (starting from 1)
        this.current_min = 1;

        this.init_record_options();

        this.map = null;
        this.current_record_nb = 0;

        this.fsd = false; // first search done

    },
    /*
     *  Inits record fields. latitude and longitude to place records on the map
     *  header_fields and body_fields are used by the record displayer to style record data. See map_controls and map_records
     */
    init_record_options: function() {
        //console.log("MapView.init_record_fields");
        this.record_options = {};
        this.record_options.latitude_field = this.fields_view.arch.attrs.latitude_field;
        this.record_options.longitude_field = this.fields_view.arch.attrs.longitude_field;
        this.record_options.header_fields = [];
        this.record_options.body_fields = [];

        for (var i=0, ii=this.fields_view.arch.children.length; i < ii; i++) {
            var child = this.fields_view.arch.children[i];
            if (child.tag === "field") {
                if (child.attrs.class === "oe_map_displayer_header") {
                    this.record_options.header_fields.push(child.attrs.name);
                }else if (child.attrs.class === "oe_map_displayer_body") {
                    this.record_options.body_fields.push(child.attrs.name);
                }
            }
        };
    },
    /**
     * Method called between init and start. Performs asynchronous calls required by start.
     */
    willStart: function() {
        //console.log("MapView.willStart: ",arguments);
        var rendered_prom = this.$el.html(QWeb.render(this.template, this)).promise();

        if (this.options.map_center_and_zoom == null) { // the map will use default config
            var dmc_prom = this.get_default_map_config().promise();
            return $.when(this._super(),rendered_prom,dmc_prom);
        }else{
            return $.when(this._super(),rendered_prom);
        }
    },
    /**
     * Method called after rendering. Mostly used to bind actions, perform asynchronous
     * calls, etc...
     *
     * By convention, this method should return an object that can be passed to $.when() 
     * to inform the caller when this widget has been initialized.
     *
     * @returns {jQuery.Deferred or any}
     */ 
    start: function() {
        //console.log("MapView.start: ",arguments);
        
        this.$el.addClass(this.fields_view.arch.attrs.class || "o_map_view");
        var options = {center: this.map_center_and_zoom[0], zoom: this.map_center_and_zoom[1]};
        var args = {view: this, options};
        this.map = new MapView.Map(args);

        return this._super();
    },

    /**
     * Handler for the result of eval_domain_and_context, actually perform the searching by calling private method
     */
    do_search: function (domain, context, group_by) {
        //console.log("MapView.do_search: ",arguments);
        var self = this;
        // only do the search if the map is attached. Workaround the auto_search option not working properly.
        if (this.map.is_attached()) {
            //console.log('this.map.is_attached()');
            this._do_search(domain, context, group_by);
        }else{
            //console.log('do_search not done, map not attached');
        }
    },
    /**
     *  private method to perform a search
     */
    _do_search: function (domain, context, group_by) {
        //console.log("MapView._do_search: ",arguments);
        if (this.domain === domain && this.group_by === group_by && this.fsd) { // the first search has been done
            this.load_records(true);
        }else{
            this.fsd = true;
            this.domain = domain;
            this.context = context;
            this.group_by = group_by;
            this.current_min = 1;
            this.load_records();
        }
    },
    /**
     *  Loads the records
     *
     *  @param {Boolean} same true if the dataset is the same. defaults to false
     */
    load_records: function (same=false) {
        //console.log("MapView.load_records: ",arguments);
        
        var self = this;
        
        if (!same){
            this.get_records(this.domain).then(function(records){
                self.current_record_nb = records.length;
                //console.log("current number of records : "+self.current_record_nb);
                self.update_pager(1);
                if (self.map.is_attached()) {
                    var opts = self.record_options;
                    self.map.reset_layer_groups().then(self.map.add_layer_group(records,opts));
                }else{
                    throw new Error(_.str.sprintf( _t("the map is not attached to its container")));
                }; 
            });
        }else{
            // supposed to happen not to get the records again, nor reset the layer groups
            console.log('SEARCH same=true');
        }

        this.do_push_state({
            min: this.current_min,
            limit: this._limit
        });
        

        return $.when();
    },

    /**
     *  @return {Array} the default map center and zoom [[lat,lng],zoom]
     */
    get_default_map_config: function () {
        //console.log("MapView.get_default_map_config");
        var self = this;

        return this._model.call('get_default_map_config').then(function(results){
            //console.log(results);
            self.map_center_and_zoom = results;
            return self.map_center_and_zoom;
        });
    },
    /**
     *  Records without latitude or without longitude will not be loaded.
     *  @return {Array} records An array of arrays of the form [ [record_fields0], [record_fields1] ... ]
     */
    get_records: function (domain=this.domain) {
        //console.log("MapView.get_records: ",arguments);
        var self = this;

        return this.dataset.read_slice(_.keys(this.fields_view.fields), {'domain':domain}).then(function(records){
            //console.log(records);
            var res = []
            for (var i=0; i<records.length; i++) {
            	if (records[i][self.record_options.latitude_field] !== 0 && records[i][self.record_options.longitude_field] !== 0) {
            		res.push(records[i]);
            	}
            }
            self.records = res;
            return res;
        });
    },
    /**
     * Handles signal for the addition of a new record (can be a creation,
     * can be the addition from a remote source, ...)
     * Not currently used, for later implementations
     *
     * The default implementation is to switch to a new record on the form view
     */
    do_add_record: function () {
        //console.log("MapView.do_add_record");
        this.select_record(null);
    },
    /**
     *  Handles signal to open the form view of a record
     */
    open_record: function (event, options) {
        //console.log("MapView.open_record: ",arguments);
        if (this.dataset.select_id(event.data.id)) {
            this.do_switch_view('form', options);
        } else {
            this.do_warn("Map: could not find id#" + event.data.id);
        }
    },
    /**
     * Instantiate and render the pager and add listeners on it.
     * Set this.pager
     * @param {jQuery} [$node] a jQuery node where the pager should be inserted
     * $node may be undefined, in which case the ListView inserts the pager into this.options.$pager
     */
    render_pager: function($node, options) {
        //console.log("MapView.render_pager: ",arguments);
        if (!this.pager && this.options.pager) {
            this.pager = new Pager(this, this.dataset.size(), 1, this._limit, options);
            this.pager.appendTo($node || this.options.$pager);
            var self = this;

            this.pager.on('pager_changed', this, function (new_state) {
                //console.log("pager_changed: ",this.pager);
                
                var limit_changed = (self._limit !== new_state.limit);

                self._limit = new_state.limit;
                self.current_min = new_state.current_min;
                var current_max = this.pager.state.current_max;
                //console.log('current_min: ',self.current_min);
                //console.log('current_max: ',current_max);
                self.map.layer_groups[self.map.current_layer_group_index].do_show_range(self.current_min-1,current_max,true);
            });
        }
    },
    /**
     * Updates the pager based on the provided dataset's information
     *
     * @param {int} current_min Min pager value
     */
    update_pager: function (current_min) { 
        //console.log("MapView.update_pager");
        var lngth = this.current_record_nb;
        //console.log("current nb of records in the pager: "+lngth);
        if (this.pager) {
            var new_state = { size: lngth, limit: this._limit };
            if (current_min) {
                new_state.current_min = current_min;
            }
            this.pager.update_state(new_state);
        }
    },
    /**
     * No idea what this is for...
     */
    do_load_state: function(state, warm) { 
        console.log("MapView.do_load_state");
        var reload = false;
        if (state.min && this.current_min !== state.min) {
            this.current_min = state.min;
            reload = true;
        }
        if (state.limit) {
            if (_.isString(state.limit)) {
                state.limit = null;
            }
            if (state.limit !== this._limit) {
                this._limit = state.limit;
                reload = true;
            }
        }
        if (reload) {
            this.load_records(true);
        }
    },
});
/**/
MapView.Map = Widget.extend({
    custom_events: {
        'map_attached': 'on_map_attached',
    },
    defaults: _.extend({},{
        center: [48.056,-2.818], // BRETAGNE
        zoom: 8, 
        minZoom: 7, 
        maxZoom: 19,
        tile_server_addr: TILE_SERVER_ADDR,
        container_id: 'lf_map',
        set_bounds_mode: 'visible',
    }),
    /**
     *  Instantiate the map and attach it to its container.
     *  
     *  @param {MapView} view View 
     */
    init: function(args) {
        //console.log("MapView.Map.init args: ",args);
        this._super(args.view);
        this.options = _.defaults(args.options||{},this.defaults);
        this.view = args.view;
        this.container_id = this.options.container_id; // the id of the container for the map
        this.tile_server_addr = this.options.tile_server_addr;

        this.layer_groups = []; // List of layer groups. 
        this.current_layer_group_index = 0;
        //this.controls = []; // maybe useful for more than one control
        this.ids_dict = {}; // object linking ids to _leaflet_ids

        this.the_map = null; // will be set in this.attach_to_container
        this.cmptry = 0; // used by this.attach_to_container
        this.attach_to_container(this.container_id,this.tile_server_addr);
        //console.log("MapView.Map inited: ", this);
    },
    /**
     *  Instantiate the record displayer for the map. See map_controls.
     */
    add_displayer: function () {
        //console.log("MapView.Map.add_displayer");
        // make sure to only add it once.
        if (!this.record_displayer) {
            this.record_displayer = new map_controls.RecordDisplayer(this.view,this.view.record_options.header_fields,this.view.record_options.body_fields);
            this.record_displayer.addTo(this.the_map);
        }else{
            console.log('this.record_displayer is already set');
        }
        
        return $.when();
    },
    /**
     *  @TODO: implement this. 
     *  buttons to add: 
     *      'clear selection' -> clears the current selection of records
     */
    add_buttons: function() {

    },
    /**
     *  Handler for custom event map_attached fired when the map is attached to its container.
     *  Adds controls and perfoms a search.
     */
    on_map_attached: function () {
        //console.log("MapView.Map.on_map_attached");=
        this.add_displayer();
        //this.add_buttons(); // later, later...

        var v = this.view;
        v.do_search(v.domain,v.context,v.group_by);
    },
    /**
     *  adds a layer group to the map's list of layer groups.
     *
     *  @param {Array} records list of records to put in the layer group.
     *  @param {Boolean} render true if we want to render the new layer_group. defaults to true.
     *  @param {Object} options A set of options used to configure the layer group.
     */
    add_layer_group: function(records, options={},render=true) {
        //console.log("MapView.Map.add_layer_group: ",arguments);
        var layer_group = new MapView.LayerGroup(this,records,options);
        this.layer_groups.push(layer_group);
        this.current_layer_group_index = this.layer_groups.length - 1;
        if (render) {
            this.render_one(layer_group);
        }
    },
    /**
     *  renders a layer group and adds it to the map
     *  
     *  @param {MapView.LayerGroup} layer_group the layer group to be rendered.
     *  @param {Boolean} set_bounds true if we want to adjust the map's bound to the newly rendered layer group. Defaults to true.
     */
    render_one: function(layer_group,set_bounds=true) {
        //console.log("MapView.Map.render_one");
        if (this.is_attached()) {
            if (!this.the_map.hasLayer(layer_group.the_layer)) {
                var self = this;
                layer_group.render(set_bounds);
            }
            return $.when();
        }else{
            throw new Error(_.str.sprintf( _t("the map is not attached to its container")));
        };
    },

    /**
     *  Renders all layer groups and adds them to the map. Not used at the moment but should be useful on group_by implementation
     */
    render_all: function() {
        //console.log("MapView.Map.render_all");
        if (this.is_attached()) {
            for (var i=0; i<this.layer_groups.length; i++) {
                this.render_one(this.layer_groups[i],false);
            };
            return $.when().then(this.set_bounds(this.options.set_bounds_mode));
        }else{
            throw new Error(_.str.sprintf( _t("the map is not attached to its container")));
        };
    },

    /**
     *  Fits the bounds of the map according to a given mode.
     *  
     *  @param {String} mode Mode to apply. Defaults to 'visible'.
     */
    set_bounds: function (mode=this.options.set_bounds_mode) {
        var bounds = new L.LatLngBounds();
        switch (mode) {
            case 'visible': 
                bounds.extend(this.get_visible_bounds());
                break;
            case 'current':
                var current_layer = this.layer_groups[this.current_layer_group_index];
                bounds.extend(current_layer.get_bounds());
                break;
            case 'current_visible': 
                var current_layer = this.layer_groups[this.current_layer_group_index];
                bounds.extend(current_layer.get_visible_bounds());
                break;
            case 'all':
                bounds.extend(this.get_bounds());
                break;
            default:
                console.log("given string doesn't match any of the available modes. modes are 'visible', 'current', current_visible' and 'all'");
        }
        this.the_map.fitBounds(bounds);
    },

    /**
     *  Returns the bounds of all markers in all layer groups
     */
    get_bounds: function() {
        //console.log("MapView.Map.get_bounds");
        var bounds = new L.LatLngBounds();

        for (var ind=0; ind<this.layer_groups.length; ind++) {
            var layer = this.layer_groups[ind];
            bounds.extend(layer.get_bounds());
        }
        return bounds;
    },

    /**
     *  Returns the bounds of all visible markers in all visible layer groups.
     */
    get_visible_bounds: function() {
        //console.log("MapView.Map.get_visiblebounds");
        var bounds = new L.LatLngBounds();

        for (var ind in this.layer_groups) {
            var layer = this.layer_groups[ind];
            if (layer.visible) {
                bounds.extend(layer.get_visible_bounds());
            }  
        }
        return bounds;
    },

    /**
     *  Looks through the layer groups and returns the one containing the record. false if not found
     *  
     *  @param {int} id Record id.
     *  @return {MapView.LayerGroup|Boolean} l Layer group containing the record, false if not found
     */
    find_record_layer_group: function(id) {
        //console.log("MapView.Map.find_record_layer_group");
        var i=false,l=false;
        for (var j=0; j<this.layer_groups.length && i===false; j++) {
            i = this.layer_groups[j].has_record(id);
            if (i) {
                l = this.layer_groups[j];
                break;
            }
        }

        if (!l) console.log("Couln't find record id#"+id+" in current layer groups.")
        
        return l;
    },
    /**
     *  Remove all layer groups from the map, then sets this.layer_groups to [].
     */
    reset_layer_groups: function() {
        //console.log("MapView.Map.reset_layer_groups");
        if (this.is_attached()) {
            var current_layer;
            for (var i=0; i<this.layer_groups.length; i++) {
                current_layer = this.layer_groups[i].the_layer;
                if (this.the_map.hasLayer(current_layer)) {
                    //console.log("removing layer...");
                    this.the_map.removeLayer(current_layer);
                }else{
                    console.log("the_map doesn't have the layer...")
                }
            };
            this.layer_groups = [];
            this.record_displayer.remove_all();
            return $.when();
        }else{
            throw new Error(_.str.sprintf( _t("the map is not attached to its container")));
        };
    },
    /**
     *  Looks for the map container, then inits the map, binds its tile layer and reload content.
     *  Workaround asynchronicity.
     *
     *  @param {String} container_id Id of the container for the map.
     *  @param {String} tile_server_addr Tile server address.
     */
    attach_to_container: function (container_id,tile_server_addr) {
        //console.log("MapView.Map.attach_to_container");
        var self = this;
        if ($('#'+container_id).length > 0) {
            this.the_map = L.map(this.container_id, { 
                center: this.options.center, 
                zoom: this.options.zoom, 
                minZoom: this.options.minZoom, 
                maxZoom: this.options.maxZoom,
            });
            L.tileLayer(tile_server_addr).addTo(this.the_map);
            
            return $.when().then(function(){
                //console.log('map attached!!!!!! by id. at try number '+(self.cmptry+1));
                self.trigger_up('map_attached');
                return true;
            });
        }else{
            if (this.cmptry<40) {
                //console.log("cmptry: "+this.cmptry);
                this.cmptry++;
                setTimeout(function(){
                    return $.when().then(self.attach_to_container(container_id,tile_server_addr));
                },40);
            }else{
                console.log('container not found after '+cmptry+' try.');
                return false;
            }
        }
    },

    is_attached: function() { return this.the_map!==null && this.the_map!==undefined; },

});

MapView.LayerGroup = Widget.extend({
    defaults: _.extend({},{
        custom_icon: true,
        // custom icon options. 
        icon_options: {
            unselected: {
                prefix: 'mdi',
                glyph: 'radiobox-blank'
            },
            selected: {
                prefix: 'mdi',
                glyph: 'radiobox-marked'
            }
        },
        visible: true, // false if none of the markers in this layer group is visible
        auto_addTo: true, // true to automatically add the_layer to the_map on rendering
    }),
    /**
     *  @constructs instance.of_map_view.MapView.LayerGroup
     *  @extends instance.web.Widget
     * 
     *  @param {MapView.Map} map map containing this layer group
     *  @param {Array} records records in this group
     *  @param {Object} options A set of options used to configure the layer group.
     */
    init: function(map, records, options) {
        //console.log("MapView.LayerGroup.init: ",arguments);
        this._super(map.view);
        this.records = records || [];
        this.options = _.defaults(options,this.defaults);
        this.icon = null;
        this.the_layer = null;

        this.visible = this.options.visible;
        if (!this.visible) this.do_toggle(false);
        
        this.map = map;
        this.current_selection = {}; // id dictionary of records currently selected. of the form id: record
    },
    /**
     *  Adds markers to the layer for each record. Adds leaflet id reference in this.map.ids_dict
     */ 
    render: function(set_bounds=true) {
        //console.log("MapView.LayerGroup.render");
        var self = this;
        if (this.the_layer!==null) {
            this.the_layer.clearLayers();
        }
        this.the_layer = new L.LayerGroup();
        var lat, lng, marker, icon, id;
        for (var i=0; i<this.records.length; i++) {
            //console.log(this.records[i]);
            lat = this.records[i][this.options.latitude_field];
            lng = this.records[i][this.options.longitude_field];

            if (this.options.custom_icon) {
                var options = this.options.icon_options.unselected;
                options['id'] = 'icon_'+this.records[i].id;
                icon = L.icon.glyph(options);
                marker = new MapView.Marker([lat, lng],this,this.records[i],{icon:icon});
            }else{
                marker = new MapView.Marker([lat, lng],this,this.records[i]);
            }
                    
            this.the_layer.addLayer(marker);
            marker.set_ids_dict_ref();
        }

        if (this.options.auto_addTo) {
            this.the_layer.addTo(this.map.the_map);
            this.visible = true;
            this.do_show_range(0,this.map.view._limit,set_bounds);
        }

        //console.log(this);
        return $.when(); 
    },
    /**
     *  Gets the bounds of all markers in this layer group
     *
     *  @return {L.LatLngBounds} bounds bounds of all markers in this layer group
     */
    get_bounds: function () {
        //console.log("MapView.LayerGroup.get_bounds");
        var bounds = new L.LatLngBounds();

        for (var id in this.the_layer._layers) {
            var layer = this.the_layer._layers[id];
            bounds.extend(layer.getBounds ? layer.getBounds() : layer.getLatLng());
        }
        return bounds;
    },
    /**
     *  Same as get_bounds, but only for visible markers
     *
     *  @return {L.LatLngBounds} bounds bounds of all visible markers in this layer group
     */
    get_visible_bounds: function () {
        //console.log("MapView.LayerGroup.get_visible_bounds");
        var bounds = new L.LatLngBounds();

        for (var id in this.the_layer._layers) {
            var layer = this.the_layer._layers[id];
            if (layer.visible) {
                bounds.extend(layer.getBounds ? layer.getBounds() : layer.getLatLng());
            }
        }
        return bounds;
    },

    /**
     *  Looks for a record by id
     *  
     *  @param {int} id id of the record
     *  @return {Boolean} found true if the record was found
     */
    has_record: function (id) {
        //console.log("MapView.LayerGroup.has_record");
        var found = false;
        for (var i=0; i<this.records.length && found === false; i++) {
            if (this.records[i].id === id) { // record found
                found = true;
                break;
            }
        }
        return found;
    },
    /**
     *  Updates the current selection of records.
     *
     *  @param {String} mode update mode. 'add' or 'remove'.
     *  @param {Object} record record to add or remove from the selection. 
     */
    update_selection: function(mode,record) { //called by this.map.record_displayer
        //console.log("MapView.LayerGroup.update_selection");
        var updated = false;
        switch (mode) {
            case 'add': 
                this.current_selection[record.id] = record;
                updated = true;
                break;
            case 'remove':
                delete this.current_selection[record.id];
                updated = true;
                break;
            default: console.log('MapView.LayerGroup.update_selection incorrect mode');
        }
        //if (updated) console.log('MapView.LayerGroup.update_selection: ',this.current_selection);
    },
    /**
     *  Clears the current selection of records. Called by the record displayer
     */
    clear_current_selection: function() {
        //console.log("MapView.LayerGroup.clear_current_selection");
        for (var k in this.current_selection) {
            var marker = this.the_layer._layers[this.map.ids_dict[k]];
            if (marker.selected) {
                marker.do_toggle_selected(false);
            }
        }
        this.current_selection = {};
    },
    /**
     *  Displays (make visible) all markers in range [ i1,i2 [
     *
     *  @param {Int} i1 Start index of the range, included in the range.
     *  @param {Int} i2 End index of the range, not included in the range.
     *  @param {Boolean} hide_rest True to hide the rest of the markers, ie to only show the given range. Defaults to false
     */
    do_show_range: function (i1,i2,hide_rest=false,set_bounds=true) {
        //console.log("MapView.LayerGroup.do_show_range");
        if (i2 > this.records.length) { // foolproofing
            i2 = this.records.length;
        }
        if (i1 < 0) { // foolproofing
            i1 = 0;
        }
        var lf_id;
        //console.log(this.map.ids_dict);
        for (var i=i1; i<i2; i++) {
            lf_id = this.map.ids_dict[this.records[i].id];
            this.the_layer._layers[lf_id].do_toggle(true);
        }
        if (hide_rest) {
            this.do_hide_range(0,i1);
            this.do_hide_range(i2,this.records.length);
        }
        if (set_bounds) this.map.set_bounds('current_visible');
    },
    /**
     *  Hides all markers in range [ i1, i2 [ 
     *
     *  @param {Int} i1 Start index of the range, included in the range.
     *  @param {Int} i2 End index of the range, not included in the range.
     *  @param {Boolean} show_rest True to show the rest of the markers, ie to only hide the given range. Defaults to false
     */
    do_hide_range: function (i1,i2,show_rest=false) {
        //console.log("MapView.LayerGroup.do_hide_range");
        if (i2 > this.records.length) { // foolproofing
            i2 = this.records.length;
        }
        if (i1 < 0) { // foolproofing
            i1 = 0;
        }
        for (var i=i1; i<i2; i++) {
            this.the_layer._layers[ this.map.ids_dict[this.records[i].id] ].do_toggle(false);
        }
        if (show_rest) {
            this.do_show_range(0,i1);
            this.do_show_range(i2,this.records.length);
        }
    },
    /**
     *  Override method from Widget.
     *  Displays (make visible) all the markers
     */
    do_show: function () {
        //console.log("MapView.LayerGroup.do_show");
        var dict = this.the_layer._layers;
        for (var key in dict) {
            if (dict[key].visible) {
                console.log('this marker is already visible');
            }else{
                dict[key].do_show();
            }
        }
        this.visible = true;
    },
    /**
     *  Override method from Widget.
     *  Hides all the markers.
     */
    do_hide: function () {
        //console.log("MapView.LayerGroup.do_hide");
        var dict = this.the_layer._layers;
        for (var key in dict) {
            if (dict[key].visible) {
                dict[key].do_hide();
            }else{
                console.log('this marker is already invisible');                
            }
        }
        this.visible = false;
    },
    /**
     *  Override method from Widget.
     *  Displays (make visible) or hides all the markers
     *
     *  @param {Boolean} [display] Use true to show the widget or false to hide it
     */
    do_toggle: function (display) {
        //console.log("MapView.LayerGroup.do_toggle");
        if (_.isBoolean(display)) {
            display ? this.do_show() : this.do_hide();
        } else {
            this.visible ? this.do_hide() : this.do_show();
        }
    },

});/**/

MapView.Marker = L.Marker.extend({
    /**
     *  @extends L.Marker
     *
     *  @param {Array} latlng Coordinates of the marker. of the form [lat,lng].
     *  @param {MapView.LayerGroup} group Layer group containing this marker.
     *  @param {Object} record Record associated to this marker.
     *  @param {Object} options A set of options used to configure the marker.
     */
    initialize: function (latlng, group, record, options) {
        //console.log("MapView.Marker.init")
        L.setOptions(this, options);
        this._latlng = L.latLng(latlng);
        this.record = record;
        this.id = record.id;
        this.group = group;
        
        // true if the marker is currently visible on the map, ie if it's on the current pager's selection
        this.visible = true;
        // true if the marker is selected. toggles from selected to unselected on click
        this.selected = false;
        // true if the marker is highlighted, ie it's selected and the mouse is over it
        this.highlighted = false;
        this.on('dblclick',this.open_record);
        this.on('click',this.do_toggle_selected);
        this.on('mouseover',this.do_toggle_highlighted);
        this.on('mouseout',this.do_toggle_highlighted);
    },
    /**
     *  Adds a reference to the map's ids_dict: this.id -> this._leaflet_id. Called when the marker is added to its layer group
     */
    set_ids_dict_ref: function() {
        //console.log("MapView.Marker.set_ids_dict_ref");
        this.group.map.ids_dict[this.id] = this._leaflet_id;
    },
    /**
     *  Opens the form view of the record
     */
    open_record: function() {
        //console.log("MapView.Marker.open_record");
        this.group.trigger_up('map_record_open', {id: this.id});
        return $.when();
    },
    /**
     *  Selects or unselects the marker. Will toggle if no parameter given.
     *
     *  @param {Boolean} [display] use true to select the marker or false to unselect it
     */
    do_toggle_selected: function(select) {
        //console.log("MapView.Marker.do_toggle_selected");
        var changed = false
        if (_.isBoolean(select)) {
            if (!this.selected === select){
                changed = true;
            }
            this.selected = select;
        } else {
            this.selected = !this.selected;
            changed = true;
        }
        //console.log('MapView.Marker id#'+this.id+' selected: '+this.selected);
        if (changed) {
            if (this.selected) {
                //console.log('marker selected: ',this);
                this.group.map.record_displayer.add_record(this.record,this.group.map.view.record_options);
            }else{
                this.group.map.record_displayer.remove_record(this.id);
            }
            this.do_toggle_highlighted(); // workaround. without it the marker would be highlighted on mouseout
            this.update_glyph();
        }
    },
    /**
     *  Highlights or downplays the marker through the record displayer.
     */
    do_toggle_highlighted: function() {
        //console.log("MapView.Marker.do_toggle_highlighted");
        if (this.selected) {
            this.highlighted = !this.highlighted;
            this.group.map.record_displayer.do_highlight_record(this.id,this.highlighted);
        }else if (this.highlighted) {
            //console.log('highlighted marker: ',this.highlighted);
            this.highlighted = !this.highlighted;
            this.group.map.record_displayer.do_highlight_record(this.id,this.highlighted,true); // we need to force because the record is not in the record displayer list of records
        }
    },
    /**
     *  Updates the icon's glyph. Called when a marker is selected, ie by click on its icon
     */
    update_glyph: function() {
        //console.log("MapView.Marker.update_glyph");
        var selected_glyph_class = this.group.options.icon_options.selected.prefix + "-" + this.group.options.icon_options.selected.glyph;
        var unselected_glyph_class = this.group.options.icon_options.unselected.prefix + "-" + this.group.options.icon_options.unselected.glyph;
        var glyph_id = '#glyph_icon_'+this.id;

        var $glyph = $(glyph_id);
        if ($glyph.length>0) {
            if ($glyph.hasClass(selected_glyph_class)) {
                $glyph.removeClass(selected_glyph_class);
                $glyph.addClass(unselected_glyph_class);
            }else{
                $glyph.removeClass(unselected_glyph_class);
                $glyph.addClass(selected_glyph_class);
            }
        }else{
            console.log("update_glyph: couldn't find glyph id"+glyph_id);
        }
    },

    /**
     *  Displays (make visible) the marker
     */
    do_show: function () {
        //console.log("MapView.Marker.do_show");
        L.DomUtil.removeClass(this._icon,'o_hidden');
        L.DomUtil.removeClass(this._shadow,'o_hidden');
        this.visible = true;
    },
    /**
     *  Hides the marker
     */
    do_hide: function () {
        //console.log("MapView.Marker.do_hide");
        L.DomUtil.addClass(this._icon,'o_hidden');
        L.DomUtil.addClass(this._shadow,'o_hidden');
        this.visible = false;
    },
    /**
     *  Displays (make visible) or hides the marker
     *
     *  @param {Boolean} [display] use true to show the marker or false to hide it
     */
    do_toggle: function (display) {
        //console.log("MapView.Marker.do_toggle: ",display);
        if (_.isBoolean(display)) {
            display ? this.do_show() : this.do_hide();
        } else {
            L.DomUtil.hasClass(this._icon,'o_hidden') ? this.do_show() : this.do_hide();
        }
    },/**/

});

    core.view_registry.add('map', MapView);

    return MapView;
})
