# README

This repository contains code for a real-time transcription service implemented in Python. The service utilizes websockets for communication and various transcription models for converting audio data into text.

`frynol_reports_generic_vishal` branch

## Files

1. **controller/realtime.py**: This file contains the main implementation of the real-time transcription service. It includes classes and functions for handling websocket connections, processing audio data, and performing transcription using different models.

2. **static/src/js/realtime.js** : This file contains the overall frontend code
## Dependencies

Ensure you have the following dependencies installed to run the code:

- `pip install -r requirements.txt`



## Usage

To use the real-time transcription service, follow these steps:

1. Install the required dependencies.
2. Set the necessary environment variables.
3. Run the server and test it.
4. Restart the server if unsuccessful.

The service will start a WebSocket server and listen for incoming connections. Clients can connect to the server and send audio data for transcription.
