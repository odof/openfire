
openerp.of_datastore_product = function (openerp) {
    var _t = openerp.web._t;

    openerp.web.form.FieldMany2One.include({

        /**
         * Mofification de get_search_result pour modifier dynamiquement la couleur dans le widget de recherche
         */
        get_search_result: function(request, response) {
            var search_val = request.term;
            var self = this;
    
            if (this.abort_last) {
                this.abort_last();
                delete this.abort_last;
            }
            var dataset = new openerp.web.DataSetStatic(this, this.field.relation, self.build_context());
    
            dataset.name_search(search_val, self.build_domain(), 'ilike',
                    this.limit + 1, function(data) {
                self.last_search = data;
                // possible selections for the m2o
                var values = _.map(data, function(x) {
                    var label = _.str.escapeHTML(x[1]);
                    if (x[0] < 0){
                        label = "<span class=\"color_orangered\">" + label + "</span>";
                    }
                    return {
                        label: label,
                        value:x[1],
                        name:x[1],
                        id:x[0]
                    };
                });

                // search more... if more results than max
                if (values.length > self.limit) {
                    var open_search_popup = function(data) {
                        self._change_int_value(null);
                        self._search_create_popup("search", data);
                    };
                    values = values.slice(0, self.limit);
                    values.push({label: _t("<em>   Search More...</em>"), action: function() {
                        if (!search_val) {
                            // search optimisation - in case user didn't enter any text we
                            // do not need to prefilter records; for big datasets (ex: more
                            // that 10.000 records) calling name_search() could be very very
                            // expensive!
                            open_search_popup();
                            return;
                        }
                        dataset.name_search(search_val, self.build_domain(),
                                            'ilike', false, open_search_popup);
                    }});
                }
                // quick create
                /* Update OpenFire : Le quick create n'est pas desire chez nous ...
                var raw_result = _(data.result).map(function(x) {return x[1];});
                if (search_val.length > 0 &&
                    !_.include(raw_result, search_val) &&
                    (!self.value || search_val !== self.value[1])) {
                    values.push({label: _.str.sprintf(_t('<em>   Create "<strong>%s</strong>"</em>'),
                            $('<span />').text(search_val).html()), action: function() {
                        self._quick_create(search_val);
                    }});
                }*/
                // create...
                values.push({label: _t("<em>   Create and Edit...</em>"), action: function() {
                    self._change_int_value(null);
                    self._search_create_popup("form", undefined, {"default_name": search_val});
                }});
    
                response(values);
            });
            this.abort_last = dataset.abort_last;
        },

        /**
         * Definition de la couleur au changement de valeur du champ one2many
         */
        _change_int_value: function(value) {
            var result = this._super.apply(this, arguments);

            if (value && value[0] < 0) {
                this.$input.css("color", "orangered");
            } else {
                this.$input.css("color", "");
            }

            return result;
        },

        /**
         * Definition de la couleur au chargement de la fenetre
         */
        set_value: function(value) {
            var result = this._super.apply(this, arguments);
            if (value && value instanceof Number) {
                self.$input.css("color", value < 0?"orangered":"");
            }
            return result
        },

    });

};
