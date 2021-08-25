# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import datetime
import logging
import time
import os
import sys
import asyncio
import threading
from azure.iot.device.aio import IoTHubModuleClient

async def main():
    try:
        if not sys.version >= "3.5.3":
            raise Exception( "The sample requires python 3.5.3+. Current version of Python: %s" % sys.version )
        print ( "IoT Hub Client for Python" )

        # The client object is used to interact with your Azure IoT hub.
        module_client = IoTHubModuleClient.create_from_edge_environment()

        # connect the client.
        await module_client.connect()
        
        async def opc_message_handler(message):
            if message.input_name=="input1":
                logging.Formatter(fmt='%(asctime)s.%(msecs)03d',datefmt='%Y-%m-%d,%H:%M:%S')
                decodedMessage=message.data.decode('utf-8')
                print("................................................................................................................ ")
                print("the data in the message received on input1 at - ",datetime.datetime.now())
                print(decodedMessage)
                print("forwarding mesage to output1 at - ",datetime.datetime.now())
                print("................................................................................................................ ")
                await module_client.send_message_to_output(decodedMessage, "output1")

        #set the message handler on the recieving inputs
        module_client.on_message_received=opc_message_handler
        
        while True:
            print ("Module is waiting for messages on input1")
            await asyncio.sleep(30)

        await module_client.disconnect()

    except Exception as e:
        print ( "Unexpected error %s " % e )
        raise

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()

    # If using Python 3.7 or above, you can use following code instead:
    # asyncio.run(main())