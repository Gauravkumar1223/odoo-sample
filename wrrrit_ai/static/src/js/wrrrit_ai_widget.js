/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, useState, onWillUpdateProps } from "@odoo/owl";

export class RangeField extends Component {
    setup() {
        this.state = useState({
            range: this.props.value || '',
        });


    }
}
RangeField.template = "wrrrit_ai.RangeField";
RangeField.props = {
    ...standardFieldProps,
};

RangeField.supportedTypes = ["integer"];

registry.category("fields").add("wrrrit_range", RangeField);
