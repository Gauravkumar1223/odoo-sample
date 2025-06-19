// stream_transcription_widget.js

odoo.define('wrrrit_ai.StreamTranscriptionWidget', function (require) {

  const { Component, useState } = owl;

  class StreamTranscriptionWidget extends Component {

    constructor() {
      super(...arguments);
      this.state = useState({ value: this.props.value });
    }

    _onValueChange(newValue) {
      // Update value in batches
      const batchSize = 5;
      const batches = newValue.match(new RegExp('.{1,' + batchSize + '}', 'g'));

      batches.forEach(batch => {
        this.state.value += batch;
        this.trigger('field-changed'); // Notify field value change
      });
    }

    render() {
    console.log('rendering stream:');
    return owl.tags.div([
    // Progress bar
    owl.tags.div({
      class: 'progress-bar',
      style: {width: this.state.value.length + '%'}
    }),

    // Text area
    owl.tags.textarea({
      value: this.state.value,
      onInput: ev => this._onValueChange(ev.target.value),
    }),
  ]);

  }
}
});