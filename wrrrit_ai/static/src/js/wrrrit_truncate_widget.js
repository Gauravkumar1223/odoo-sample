/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState, onWillUpdateProps } from "@odoo/owl";

export class WrrritTruncate extends Component {
    setup() {
        // console.log("Setting up WrrritTruncate component...");

        // Log field value and max_len
        // console.log("Field Value:", this.props.value);
        // console.log("Max Length:", this.props.max_len);

        // Initialize truncated string based on input value and max_len
        let initialTruncatedValue = this.getTruncatedString(this.props.value, this.props.max_len);
        // console.log("Initial truncated value:", initialTruncatedValue);

        this.state = useState({
            truncatedString: initialTruncatedValue,
            styled : this.props.styled
        });

        onWillUpdateProps((nextProps) => {
            let updatedTruncatedValue = this.getTruncatedString(nextProps.value, nextProps.max_len);
            // console.log("Updated truncated value based on new props:", updatedTruncatedValue);
            this.state.truncatedString = updatedTruncatedValue;
        });
    }

    getTruncatedString(string, max_len = 20) {
        // console.log("Truncating string:", string, "with max length:", max_len);

        if (typeof string !== 'string') {
            // console.warn('Expected a string but got:', string);
            return "";
        }

        if (string.length <= max_len) {
            return string;
        }

        let truncated = string.substring(0, max_len - 3) + "...";
        // console.log("Resulting truncated string:", truncated);
        return truncated;
    }

    // No need for a render method since you are using a qweb template to render your component
}

WrrritTruncate.template = "wrrrit_ai.WrrritTruncate";

WrrritTruncate.props = {
    ...standardFieldProps,
    max_len: { type: Number, optional: true, default: 20 }, // Provide a default value
    styled: { type: Boolean, optional: true, default: false }
};

WrrritTruncate.extractProps = ({attrs}) => {
    let options = attrs.options || {}; // Ensure that options are available even if undefined
    return {
        max_len: options.max_len || 20 ,
        styled : options.styled // Default value if it's not set
    };
};

registry.category("fields").add("wrrrit_truncate", WrrritTruncate);
