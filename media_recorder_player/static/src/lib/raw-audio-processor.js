// raw-audio-processor.js
class RawAudioProcessor extends AudioWorkletProcessor {
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];

        for (let channel = 0; channel < input.length; channel++) {
            const inputChannel = input[channel];
            const outputChannel = output[channel];

            if (inputChannel) {
                for (let i = 0; i < inputChannel.length; i++) {
                    // You can process your raw audio data here
                    outputChannel[i] = inputChannel[i];
                }
            }
        }
        return true;
    }
}

registerProcessor('raw-audio-processor', RawAudioProcessor);
