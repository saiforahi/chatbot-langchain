# listeners.py
from application.helper import get_location_from_lat_lng
from .socket import socketio


# from deepgram import DeepgramClient
# import os
# import asyncio
# from aiohttp import web

# # Load Deepgram API Key
# dg_client = DeepgramClient('8a9f693932164e20f2d4597f8b42d60f442f77ad')

# async def process_audio(audio_data):
#     try:
#         # Send audio data to Deepgram for transcription
#         deepgram_socket = await connect_to_deepgram()
#         deepgram_socket.send(audio_data)

#         # Receive transcription result from Deepgram
#         result = await deepgram_socket.receive()
#         if 'channel' in result:
#             transcript = result['channel']['alternatives'][0]['transcript']
#             if transcript:
#                 socketio.emit('transcription_result', transcript)
#     except Exception as e:
#         print(f'Error processing audio: {e}')

# async def connect_to_deepgram():
#     try:
#         # Create a Deepgram socket for live transcription
#         socket = await dg_client.transcription.live({'punctuate': True, 'interim_results': False})
#         return socket
#     except Exception as e:
#         print(f'Could not open socket: {e}')

def register_socket_listeners():
    @socketio.on('message')
    def handle_message(data):
        print('Received message:', data)

    @socketio.on('disconnect')
    def handle_disconnected():
        print('Client disconnected')

    @socketio.on('connect')
    def handle_connected():
        # if data:
        #     # asyncio.create_task(process_audio(data))
        #     print('Client connected with data:', data)

        print('Client connected')

    @socketio.on('get-location')
    def handle_get_location(data):
        print('------------------- Received message:', data)
        location = get_location_from_lat_lng(data['latitude'], data['longitude'])
        socketio.emit("user-location", {"data": {"location": location, "latitude": data['latitude'],"longitude": data['longitude']}})
