# |-----------------------------------------------------------------------------
# |            This source code is provided under the Apache 2.0 license      --
# |  and is provided AS IS with no warranty or guarantee of fit for purpose.  --
# |                See the project's LICENSE.md for details.                  --
# |           Copyright Refinitiv 2020-2021. All rights reserved.             --
# |-----------------------------------------------------------------------------

# |-----------------------------------------------------------------------------
# |         Refinitiv Eikon API demo app/module to get symbology              --
# |-----------------------------------------------------------------------------

# Import the required libraries for Eikon and JSON operations
import eikon as ek
import logging
import json

class DAPISessionManagement:
    
    dapi_app_key = ''

    # Constructor function
    def __init__(self, app_key):
        self.dapi_app_key = app_key
        ek.set_app_key(self.dapi_app_key)
    
    '''
    convert symbol to targe instrument code type with ek.get_data function. The supported fields are 
        - TR.RIC
        - TR.ISIN
        - TR.SEDOL
        - TR.CUSIP
        - TR.LipperRICCode
        - TR.OrganizationID
    '''
    def convert_symbology(self, symbol, target_symbol_type = 'TR.ISIN'):
        converted_result = True
        try:
            response = ek.get_data(symbol,target_symbol_type, raw_output = True)
            if 'error' in response or not response['data'][0][1]: # The get_data can returns both 'error' and just empty/null result 
                converted_result = False

            return converted_result, response
        except Exception as ex:
            logging.error('Data API: get_data exception failure: %s' % ex)
            return False, None
    
    # verify if Eikon Data API is connect to Refinitiv Workspace/Eikon Desktop application
    def verify_desktop_connection(self):
        return ek.get_port_number()

# =============================== Main Process, For verifying your Eikon Data API Access purpose ============================
if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s: %(levelname)s:%(name)s :%(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')

    # Authentication Variables
    _app_key = '---YOUR DATA API APPKEY---'


    """
    Input above DAPI App Key information and run this module with the following command in a console
    $>python dapi_session.py
    """
    print('Setting Eikon Data API App Key')
    dapi_session = DAPISessionManagement(_app_key)
    if dapi_session.verify_desktop_connection(): #if init session with Refinitiv Workspace/Eikon Desktop success
        result, response = dapi_session.convert_symbology('IBM.N','TR.ISIN')
        print(response)