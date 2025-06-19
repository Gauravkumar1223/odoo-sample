odoo.define('wrrrit_ai.wrrrit_ai_document', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer');

    FormRenderer.include({
        _renderView: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.state.model === 'wrrrit.ai.document' && self.mode === 'readonly') {
                    var recordID = self.state.res_id;
                    var iframe = self.$el.find("#pdf_frame");
                    var newSrc = "/web/content/?model=wrrrit.ai.document&field=file&id=" + recordID + "&filename=name";
                    iframe.attr("src", newSrc);
                }
            });
        },
    });
});
