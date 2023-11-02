odoo.define('of_crm_project.of_survey_form', function (require) {
'use strict';

    var OFSurveyFormWidget = require('of_survey.form');

    function sleep (time) {
      return new Promise((resolve) => setTimeout(resolve, time));
    }

    OFSurveyFormWidget.include({
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var show_start = $('.show_start').attr('data-show');
                var show_end = $('.show_end').attr('data-show');
                var survey_id = $('.show_end').attr('crm-lead-id');
                if (show_start=='no'){
                    self._submitForm({});
                }

                if (show_end=='no'){
                    console.log("show_end : no")
                    window.location = "/web/#id="+survey_id+"&model=crm.lead&view_type=form";
                }


            });
        },

    });

    return OFSurveyFormWidget;

});
