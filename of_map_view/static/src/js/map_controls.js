odoo.define('of_map_view.map_controls', function (require) {
"use strict";

var core = require('web.core');
var MapRecord = require('of_map_view.map_record');
var Model = require('web.DataModel');
var session = require('web.session');
var time = require('web.time');

var qweb = core.qweb;
var _t = core._t;
var _lt = core._lt;

L.Control.RecordDisplayer = L.Control.extend({
    options: {
        position: 'topleft'
    },
    /**
     *	Inits the displayer.
     */
    initialize: function(view,options) {
        //console.log('RecordDisplayer.initialize');
        L.Util.setOptions(this, options);
        this.view = view;
        this.map = this.view.map;
        this.fields = this.view.fields;
        this.records = {};
        this.qweb = options.qweb;
        this.many2manys = this.view.many2manys;
        this.m2m_context = this.view.m2m_context;
    },
    /**
     *  Renders the displayer.
     */
    onAdd: function(map) {
        //console.log('RecordDisplayer.onAdd');
        var container_tag = 'div';
        var container_class = 'o_record_display_control';
        this.container = L.DomUtil.create(container_tag, container_class);
        this.container.style.backgroundColor = 'transparent';

        return this.container;
    },
    /**
     *
     */
    onRemove: function(map) {
        // Tear down the control.
    },
    /**
     *	Adds a record to the displayer.
     *
     *	@param {Object} marker marker containing the record to add.
     *	@param {Object} options A set of options used to configure the map_record.
     */
    add_record: function(marker,options) {
        //console.log('RecordDisplayer.add_record: ',marker,options);
        var map_record = new MapRecord(this.view,marker,this,options);
        this.records[marker.id] = map_record;
        map_record.appendTo(this.container);

        var layer_group = this.map.layer_groups[this.map.current_layer_group_index];
        layer_group.update_selection('add',marker.record);
    },
    /**
     *  Remove all records from the displayer.
     */
    remove_all: function() {
        //console.log("RecordDisplayer.remove_all");
        var layer_group = this.map.layer_groups[this.map.current_layer_group_index];
        if (layer_group) {
            layer_group.clear_current_selection();
        }
        for (var k in this.records) {
            this.records[k].destroy();
            delete this.records[k];
        }
        this.records = [];
        $('.record_display_control').empty();
    },
    /**
     *	Removes a record from the displayer and updates its layer group current selection
     *
     *	@param {int} id id of the record to remove.
     */
    remove_record: function(id) {
        //console.log("RecordDisplayer.remove_record");
        if (this.records[id]) {
            var layer_group = this.map.layer_groups[this.map.current_layer_group_index];
            layer_group.update_selection('remove',this.records[id]);

            this.records[id].destroy();
            delete this.records[id];
            var str = '#map_record_'+id;
            //console.log('str: ',str);
            $(str).remove();
        }else{
            throw new Error(_.str.sprintf( _t("couldn't find record id#"+id)))
        }
    },
    get_record_ids: function() {
        var record_ids = [];
        for (var k in this.records) {
            record_ids.push(parseInt(k));
        }
        return record_ids;
    },
    /**
     *  Handles signal to highlight or downplay a record marker and map_record
     *
     *	@param {int} id of the record to highlight
     *	@param {Boolean} on true to highlight, false to downplay
     *	@param {Boolean} force true to force the code to be executed even if the record is not selected. Workaround issue of unselected-yet-highlighted records. defaults to false.
     */
    do_highlight_record: function (id,on,force=false) {
        //console.log("RecordDisplayer.do_highlight_record");
        if (this.records[id] || force) { // equivalent to marker selected
            var glyph_icon_id = '#glyph_icon_'+id;
            var map_record_id = '#map_record_'+id;
            var $glyph = $(glyph_icon_id);
            var $map_record = $(map_record_id);

            //console.log('$glyph: ',$glyph);
            //console.log('$map_record: ',$map_record);

            var icon_found = $glyph.length > 0;
            var record_found = $map_record.length > 0;
            if (icon_found && record_found) {
                //console.log('found glyph by id! id#'+glyph_icon_id);
                if (on) {
                    var layer = this.map.find_record_layer_group(id);
                    //console.log('LAYER: ',layer);
                    if (layer) {
                        var marker = layer.the_layer._layers[ this.map.ids_dict[id] ];
                    }

                    if (!marker.visible) { // the marker is not visible
                        $glyph.css('color','lightGrey');
                        $map_record.css('background-color','lightGrey');
                    }else{
                        $glyph.css('color','yellow');
                        $map_record.css('background-color','yellow');
                    }
                }else{
                    $glyph.css('color','white');
                    $map_record.css('background-color','white');
                }
            }else if (icon_found) { // when a record is getting unselected for example
                //console.log('found glyph by id! id#'+glyph_icon_id);
                if (on) {
                    $glyph.css('color','yellow');
                }else{
                    $glyph.css('color','white');
                }
            }else{
                if (!icon_found) console.log('could not find glyph by id! id'+glyph_icon_id);
                if (!record_found) console.log('could not find map_record by id! id'+map_record_id);
            }
        }else{
            console.log("couldn't find record id#"+id);
        }
    },
});

L.control.record_displayer = function(view,options) {
    return new L.Control.RecordDisplayer(view,options);
};

L.Control.NoContentDisplayer = L.Control.extend({
    options: {
        position: 'topleft'
    },
    /**
     *	Inits the displayer.
     */
    initialize: function(view,options) {
        L.Util.setOptions(this, options);
        this.view = view;
    },
    /**
     *	Renders the container and hides the control
     */
    onAdd: function (map) {
        var container_tag = 'div';
        var container_class = 'o_nocontent_display_control';
        this.container = L.DomUtil.create(container_tag, container_class);
        this.container.style.backgroundColor = 'white';

        this.content = '';
        this.do_hide();

        return this.container;
    },

    onRemove: function (map) {
        // when removed
    },
    /**
     *	Empties the container and updates its content
     */
    update_content: function() {
        this._compute_content();

        $('.o_nocontent_display_control').empty().append(this.content);
    },
    /**
     *  computes the control's content
     */
    _compute_content: function() {
        this.content = '';
        // number of nondisplayable records
        /*var nb_nd_records = this.view.nondisplayable_records.length;
        if (nb_nd_records > 1) { // records were found but none of them is displayable on the map
            this.content += nb_nd_records + ' ' + _t('records matching your search were found, but none of them is displayable on the map (invalid GPS coordinates). ');
        }else if (nb_nd_records > 0) { // 1 record was found but none of them is displayable on the map
            this.content += nb_nd_records + ' ' + _t('record matching your search was found, but it is not displayable on the map (invalid GPS coordinates). ');
        }else{
            this.content += _t('no record matching your search was found.');
        }*/
        this.content += _t('no displayable record matching your search was found.');
    },

    /**
     *  Displays (make visible) the control
     */
    do_show: function () {
        //console.log("MapView.Marker.do_show");
        L.DomUtil.removeClass(this.container,'o_hidden');
        this.visible = true;
    },
    /**
     *  Hides the control
     */
    do_hide: function () {
        //console.log("MapView.Marker.do_hide");
        L.DomUtil.addClass(this.container,'o_hidden');
        this.visible = false;
    },
    /**
     *  Displays (make visible) or hides the control
     *
     *  @param {Boolean} [display] use true to show the control or false to hide it
     */
    do_toggle: function(display) {
        //console.log("NoContentDisplayer.do_toggle: ",display);
        if (_.isBoolean(display)) {
            display ? this.do_show() : this.do_hide();
        } else {
            L.DomUtil.hasClass(this.container,'o_hidden') ? this.do_show() : this.do_hide();
        }
    },

});

L.Control.LegendDisplayer = L.Control.extend({
    options: {
        position: 'bottomright'
    },
    /**
     *  Inits the displayer.
     */
    initialize: function(view,options) {
        L.Util.setOptions(this, options);
        this.view = view;
    },
    /**
     *  Renders the container and hides the control
     */
    onAdd: function (map) {
        var self = this
        var container_tag = 'div';
        var container_class = 'of_legend_control';
        this.container = L.DomUtil.create(container_tag, container_class);

        this.add_legends();

        return this.container;
    },

    add_legends: function () {
        var self = this;
        var legend;
        for (var i in this.options.legends) {
            legend = this.options.legends[i];
            //console.log("legend: ",legend);
            var context = self.options.context;
            $.when(new Model(this.view.dataset.model).call(legend.method, context))
            .then(function (result){
                //console.log("result: ", result);
                if (result) {
                  var html = qweb.render(legend.template, { title: result.title, lines: result.values });
                  self.container.innerHTML += html;
                }
            });
        }
    },

    onRemove: function (map) {
        // when removed
    },

    /**
     *  Displays (make visible) the control
     */
    do_show: function () {
        //console.log("MapView.Marker.do_show");
        L.DomUtil.removeClass(this.container,'o_hidden');
        this.visible = true;
    },
    /**
     *  Hides the control
     */
    do_hide: function () {
        //console.log("MapView.Marker.do_hide");
        L.DomUtil.addClass(this.container,'o_hidden');
        this.visible = false;
    },
    /**
     *  Displays (make visible) or hides the control
     *
     *  @param {Boolean} [display] use true to show the control or false to hide it
     */
    do_toggle: function(display) {
        //console.log("NoContentDisplayer.do_toggle: ",display);
        if (_.isBoolean(display)) {
            display ? this.do_show() : this.do_hide();
        } else {
            L.DomUtil.hasClass(this.container,'o_hidden') ? this.do_show() : this.do_hide();
        }
    },

});

L.control.legend_displayer = function(view,options) {
    return new L.Control.LegendDisplayer(view,options);
};

/*// not implemented yet
L.Control.TopRightButtons = L.Control.extend({

	options: {
		position: 'topleft'
  	},

  	initialize: function (options) {
    	// constructor
    	console.log('TopRightButtons: initialize');
  		console.log('TopRightButtons: ',this);
  		L.Util.setOptions(this, options);
  	},

  	onAdd: function (map) {
  		//this.container = L.DomUtil.create('input',container_class);
    	//this.container.type="button";
    	// happens after added to map
  	},

  	onRemove: function (map) {
    	// when removed
  	}

});*/

return {
    RecordDisplayer: L.Control.RecordDisplayer,
    NoContentDisplayer: L.Control.NoContentDisplayer,
    LegendDisplayer: L.Control.LegendDisplayer,
};

});