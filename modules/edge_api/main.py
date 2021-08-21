# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import time
import os
import sys
import asyncio
from six.moves import input
import threading
from azure.iot.device.aio import IoTHubModuleClient
from flask import Flask

port =int(os.environ.get("port",5000))
print("port is ",port)

# Initialize flask app
app = Flask(__name__)

# Create an endpoint
@app.route('/predict')
def predict_chiller_condition():
    print("api func called")
    predictedVal=3
    return 'predicted value is '+str(predictedVal)

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=port)