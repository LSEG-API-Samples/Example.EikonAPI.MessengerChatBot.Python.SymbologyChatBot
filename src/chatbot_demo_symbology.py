# |-----------------------------------------------------------------------------
# |            This source code is provided under the Apache 2.0 license      --
# |  and is provided AS IS with no warranty or guarantee of fit for purpose.  --
# |                See the project's LICENSE.md for details.                  --
# |           Copyright Refinitiv 2020. All rights reserved.                  --
# |-----------------------------------------------------------------------------

# |-----------------------------------------------------------------------------
# |          Refinitiv Messenger BOT API via HTTP REST and WebSocket          --
# |-----------------------------------------------------------------------------

import sys
import time
import getopt
import requests
import socket
import json
import websocket
import threading
import random
import logging

from string import Template
import re

from rdp_token import RDPTokenManagement
import eikon as ek

# Input your Bot Username
bot_username = ''
# Input Bot Password
bot_password = ''
# Input your Messenger account AppKey.
app_key = ''


# Input your Refinitiv Workspace/Eikon Desktop Data API App Key
data_api_appkey = ''#'---YOUR DATA API APPKEY---'

# Setting Log level the supported value is 'logging.INFO' and 'logging.DEBUG'
log_level = logging.DEBUG

# Authentication and connection objectscls
auth_token = None
rdp_token = None
access_token = None
expire_time = 0
logged_in = False

refresh_token = None
# Chatroom objects
chatroom_id = None
joined_rooms = None

# Please verify below URL is correct via the WS lookup
ws_url = 'wss://api.collab.refinitiv.com/services/nt/api/messenger/v1/stream'
gw_url = 'https://api.refinitiv.com'
bot_api_base_path = '/messenger/beta1'

# Symbology Variables
symbology_request_pattern = r'Please convert (?P<symbol>.*) from (?P<from>.*) to (?P<to>.*)'
response_template = Template('@$sender, the $to_symbol_type instrument code of  $symbol is $converted_symbol')
response_error_template = Template('@$sender, the $to_symbol_type instrument code of $symbol is not available')
help_message = ('You can ask me to convert instrument code with this command\n'
                '"Please convert <symbol> from <symbol type> to <symbole type  to convert to>"\n'
                '- The supported <symbol type> are: CUSIP, ISIN, SEDOL, RIC, ticker, lipperID and IMO\n'
                '- The supported <symbole type  to convert to> are: CUSIP, ISIN, SEDOL, RIC, ticker, lipperID, IMO and OAPermID\n'
                '\n'
                'Example:\n'
                'Please convert IBM.N from RIC to ISIN')

# =============================== RDP and Messenger BOT API functions ========================================


def authen_rdp(rdp_token_object):  # Call RDPTokenManagement to get authentication
    # Based on WebSocket application behavior, the Authentication will not read/write Token from rest-token.txt file
    auth_token = rdp_token_object.get_token(save_token_to_file=False,  current_refresh_token = refresh_token)
    if auth_token:
        # return RDP access token (sts_token) ,refresh_token , expire_in values and RDP login status
        return auth_token['access_token'], auth_token['refresh_token'], auth_token['expires_in'] , True
    else:
        return None,None, 0, False


# Get List of Chatrooms Function via HTTP REST
def list_chatrooms(access_token, room_is_managed=False):

    if room_is_managed:
        url = '{}{}/managed_chatrooms'.format(gw_url, bot_api_base_path)
    else:
        url = '{}{}/chatrooms'.format(gw_url, bot_api_base_path)

    response = None
    try:
        # Send a HTTP request message with Python requests module
        response = requests.get(
            url, headers={'Authorization': 'Bearer {}'.format(access_token)})
    except requests.exceptions.RequestException as e:
        logging.error('Messenger BOT API: List Chatroom exception failure: %s' % e)

    if response.status_code == 200:  # HTTP Status 'OK'
        print('Messenger BOT API: get chatroom  success')
        logging.info('Receive: %s' % (json.dumps(response.json(),sort_keys=True, indent=2, separators=(',', ':'))))
        return response.status_code, response.json()
    else:
        print('Messenger BOT API: get chatroom result failure:',response.status_code, response.reason)
        print('Text:', response.text)
        return response.status_code, None
    


def join_chatroom(access_token, room_id=None, room_is_managed=False):  # Join chatroom
    joined_rooms = []
    if room_is_managed:
        url = '{}{}/managed_chatrooms/{}/join'.format(
            gw_url, bot_api_base_path, room_id)
    else:
        url = '{}{}/chatrooms/{}/join'.format(gw_url,
                                              bot_api_base_path, room_id)

    response = None
    try:
        # Send a HTTP request message with Python requests module
        response = requests.post(
            url, headers={'Authorization': 'Bearer {}'.format(access_token)})
    except requests.exceptions.RequestException as e:
        logging.error('Messenger BOT API: join chatroom exception failure: %s' % e)

    if response.status_code == 200:  # HTTP Status 'OK'
        joined_rooms.append(room_id)
        print('Messenger BOT API: join chatroom success')
        logging.info('Receive: %s' % (json.dumps(response.json(),sort_keys=True, indent=2, separators=(',', ':'))))
    else:
        print('Messenger BOT API: join chatroom result failure:',
              response.status_code, response.reason)
        print('Text:', response.text)

    return joined_rooms



# Posting Messages to a Chatroom via HTTP REST
def post_message_to_chatroom(access_token,  joined_rooms, room_id=None,  text='', room_is_managed=False):
    if room_id not in joined_rooms:
        joined_rooms = join_chatroom(access_token, room_id, room_is_managed)

    if joined_rooms:
        if room_is_managed:
            url = '{}{}/managed_chatrooms/{}/post'.format(
                gw_url, bot_api_base_path, room_id)
        else:
            url = '{}{}/chatrooms/{}/post'.format(
                gw_url, bot_api_base_path, room_id)

        body = {
            'message': text
        }

        # Print for debugging purpose
        logging.info('Sent: %s' % (json.dumps(
            body, sort_keys=True, indent=2, separators=(',', ':'))))

        response = None
        try:
            # Send a HTTP request message with Python requests module
            response = requests.post(
                url=url, data=json.dumps(body), headers={'Authorization': 'Bearer {}'.format(access_token)})
        except requests.exceptions.RequestException as e:
            logging.error('Messenger BOT API: post message to exception failure: %s ' % e)

        if response.status_code == 200:  # HTTP Status 'OK'
            joined_rooms.append(room_id)
            print('Messenger BOT API: post message to chatroom success')
            # Print for debugging purpose
            logging.info('Receive: %s' % (json.dumps(
                response.json(), sort_keys=True, indent=2, separators=(',', ':'))))
        else:
            print('Messenger BOT API: post message to failure:',
                  response.status_code, response.reason)
            print('Text:', response.text)
    pass


# Leave a joined Chatroom
def leave_chatroom(access_token, joined_rooms, room_id=None, room_is_managed=False):

    if room_id in joined_rooms:
        if room_is_managed:
            url = '{}{}/managed_chatrooms/{}/leave'.format(
                gw_url, bot_api_base_path, room_id)
        else:
            url = '{}{}/chatrooms/{}/leave'.format(
                gw_url, bot_api_base_path, room_id)

        response = None
        try:
            # Send a HTTP request message with Python requests module
            response = requests.post(
                url, headers={'Authorization': 'Bearer {}'.format(access_token)})
        except requests.exceptions.RequestException as e:
            logging.error('Messenger BOT API: leave chatroom exception failure: %s' % e)

        if response.status_code == 200:  # HTTP Status 'OK'
            print('Messenger BOT API: leave chatroom success')
            logging.info('Receive: %s' % (json.dumps(response.json(), sort_keys=True, indent=2, separators=(',', ':'))))
        else:
            print('Messenger BOT API: leave chatroom failure:',
                  response.status_code, response.reason)
            print('Text:', response.text)

        joined_rooms.remove(room_id)

    return joined_rooms

# =============================== Data API functions ========================================

def convert_symbology(symbol, original_symbol_type = 'RIC', target_symbol_type = 'ISIN'):
    try:
        response = ek.get_symbology(symbol, from_symbol_type= original_symbol_type, to_symbol_type = target_symbol_type, raw_output = True)
        converted_result = True
        converted_symbol = None
        for key in response['mappedSymbols'][0]['bestMatch'].keys():
            if key == 'error':
                converted_result = False

            converted_symbol = response['mappedSymbols'][0]['bestMatch'][key]
        return converted_result, converted_symbol
    except Exception as ex:
        logging.error('Data API: get_symbology exception failure: %s' % ex)
        return False, None

# =============================== WebSocket functions ========================================


def on_message(_, message):  # Called when message received, parse message into JSON for processing
    message_json = json.loads(message)
    logging.debug('Received: %s' % (json.dumps(message_json, sort_keys=True, indent=2, separators=(',', ':'))))
    process_message(message_json)


def on_error(_, error):  # Called when websocket error has occurred
    logging.error('Error: %s' % (error))


def on_close(_):  # Called when websocket is closed
    logging.error('Receive: onclose event. WebSocket Connection Closed')
    leave_chatroom(access_token, joined_rooms, chatroom_id)
    # Abort application
    sys.exit("Abort application")


def on_open(_):  # Called when handshake is complete and websocket is open, send login
    logging.info('Receive: onopen event. WebSocket Connection is established')
    send_ws_connect_request(access_token)


# Send a connection request to Messenger ChatBot API WebSocket server
def send_ws_connect_request(access_token):

    # create connection request message in JSON format
    connect_request_msg = {
        'reqId': str(random.randint(0, 1000000)),
        'command': 'connect',
        'payload': {
            'stsToken': access_token
        }
    }
    try:
        web_socket_app.send(json.dumps(connect_request_msg))
    except Exception as error:
        #print('send_ws_connect_request Exception:', error)
        logging.error('send_ws_connect_request exception: %s' % (error))

    logging.info('Sent: %s' % (json.dumps(connect_request_msg, sort_keys=True, indent=2, separators=(',', ':'))))


# Function for Refreshing Tokens.  Auth Tokens need to be refreshed within 5 minutes for the WebSocket to persist
def send_ws_keepalive(access_token):

    # create connection request message in JSON format
    connect_request_msg = {
        'reqId': str(random.randint(0, 1000000)),
        'command': 'authenticate',
        'payload': {
            'stsToken': access_token
        }
    }
    try:
        web_socket_app.send(json.dumps(connect_request_msg))
    except Exception as error:
        #print('send_ws_connect_request Exception :', error)
        logging.error('send_ws_connect_request exception: %s' % (error))
    
    logging.info('Sent: %s' % (json.dumps(connect_request_msg, sort_keys=True, indent=2, separators=(',', ':'))))


def process_message(message_json):  # Process incoming message from a joined Chatroom

    message_event = message_json['event']

    if message_event == 'chatroomPost':
        try:
            incoming_msg = message_json['post']['message']
            print('Receive text message: %s' % (incoming_msg))
            if incoming_msg == '/help':
                #r'Please convert (?P<symbol>.*) from (?P<from>.*) to (?P<to>.*)'
                
                post_message_to_chatroom(access_token, joined_rooms, chatroom_id, help_message)
            else:
                try:
                    match = re.match(symbology_request_pattern, incoming_msg)
                    if match:
                        symbol = match.group('symbol')
                        from_symbol_type = match.group('from')
                        to_symbol_type = match.group('to')

                        result, converted_code = convert_symbology(symbol,from_symbol_type, to_symbol_type )
                        sender = message_json['post']['sender']['email']
                        if result:
                             response_message = response_template.substitute(sender = sender, 
                             converted_symbol = converted_code, 
                             symbol = symbol, 
                             to_symbol_type = to_symbol_type)
                        else:
                            # response_error_template = Template('@$sender, the $to_symbol_type of $from_symbol_type $symbol is not available')
                            response_message = response_error_template.substitute(sender = sender, to_symbol_type = to_symbol_type,  symbol = symbol)
                       
                        post_message_to_chatroom( access_token, joined_rooms, chatroom_id, response_message)

                except AttributeError as attrib_error:
                    print('IOError Exception: %s' % attrib_error)


        except Exception as error:
            logging.error('Post meesage to a Chatroom fail : %s' % error)


# =============================== Main Process ========================================
# Running the tutorial
if __name__ == '__main__':

    # Setting Python Logging
    logging.basicConfig(format='%(asctime)s: %(levelname)s:%(name)s :%(message)s', level=log_level, datefmt='%Y-%m-%d %H:%M:%S')

    print('Setting Eikon Data API App Key')
    ek.set_app_key(data_api_appkey)

    print('Getting RDP Authentication Token')

    # Create and initiate RDPTokenManagement object
    rdp_token = RDPTokenManagement(bot_username, bot_password, app_key, 30)

    # Authenticate with RDP Token service
    access_token, refresh_token, expire_time, logged_in = authen_rdp(rdp_token)
    # if not auth_token:
    if not access_token:
        # Abort application
        sys.exit(1)

    print('Successfully Authenticated ')

    # List associated Chatrooms
    print('Get Rooms ')
    status, chatroom_respone = list_chatrooms(access_token)

    if not chatroom_respone:
        # Abort application
        sys.exit(1)

    #print(json.dumps(chatroom_respone, sort_keys=True,indent=2, separators=(',', ':')))

    chatroom_id = chatroom_respone['chatrooms'][0]['chatroomId']
    # print('Chatroom ID is ', chatroom_id)

    # Join associated Chatroom
    print('Join Rooms ')
    joined_rooms = join_chatroom(access_token, chatroom_id)
    # print('joined_rooms is ', joined_rooms)

    if not joined_rooms:
        # Abort application
        sys.exit(1)

    # Send Greeting message
    post_message_to_chatroom( access_token, joined_rooms, chatroom_id, 'Hi, I am a chatbot symbology converter.\n\n' + help_message)
    # Connect to a Chatroom via a WebSocket connection
    print('Connecting to WebSocket %s ... ' % (ws_url))
    #websocket.enableTrace(True)
    web_socket_app = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        subprotocols=['messenger-json'])

    web_socket_app.on_open = on_open
    # Event loop
    wst = threading.Thread(
        target=web_socket_app.run_forever,
        kwargs={'sslopt': {'check_hostname': False}})
    wst.start()

    try:
        while True:
            # Give 60 seconds to obtain the new security token and send reissue
            #logging.debug('expire_time = %s' %(expire_time))
            if int(expire_time) > 60: 
                time.sleep(int(expire_time) - 60) 
            else:
                # Fail the refresh since value too small
                # Abort application
                sys.exit(1)

            print('Refresh Token ')
            access_token, refresh_token, expire_time, logged_in = authen_rdp(rdp_token)
            if not access_token:
                # Abort application
                sys.exit(1)
            # Update authentication token to the WebSocket connection.
            if logged_in:
                send_ws_keepalive(access_token)
    except KeyboardInterrupt:
        web_socket_app.close()
