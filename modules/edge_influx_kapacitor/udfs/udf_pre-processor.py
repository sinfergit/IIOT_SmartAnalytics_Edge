from kapacitor.udf.agent import Agent, Handler
from kapacitor.udf import udf_pb2
import tensorflow as tf
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.models import load_model
import json
import logging
import numpy as np
import pandas as pd
from pickle import dump,load

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger()

class FddPredictorHandler(Handler):
    def __init__(self,agent):
        # Define what your UDF wants and what will it provides and options
        logger.info('preprocessor___init__trigger')
        self._agent = agent
        self._size = 10
        self._points = []
        self._pointerList = []
        self._state = {}
        self._sensorColumns=["TWE_set","TEI","TWEI","TEO","TWEO","TCI","TWCI","TCO","TWCO","TSI","TSO","TBI","TBO","Cond Tons","Cooling Tons","Shared Cond Tons","Cond Energy Balance","Evap Tons"
    ,"Shared Evap Tons","Building Tons","Evap Energy Balance","kW","COP","FWC","FWE","TEA","TCA","TRE","PRE","TRC","PRC","TRC_sub","T_suc","Tsh_suc","TR_dis","Tsh_dis","P_lift"
    ,"Amps","RLA%","Heat Balance%","Tolerance%","Unit Status","Active Fault","TO_sump","TO_feed","PO_feed","PO_net","TWCD","TWED","VSS","VSL","VH","VM","VC","VE","VW"
    ,"TWI","TWO","THI","THO","FWW","FWH","FWB"]
        self._columnCount = len(self._sensorColumns)

    def info(self):
        logger.info('preprocessor_info trigger')
        response = udf_pb2.Response()
        response.info.wants = udf_pb2.BATCH
        response.info.provides = udf_pb2.STREAM
        response.info.options['size'].valueTypes.append(udf_pb2.INT)
        logger.info(tf.__version__)
        return response

    def init(self,init_req):
        # Define what your UDF expects as options when parsing TICKScript
        logger.info('preprocessor_INIT trigger')
        for opt in init_req.options:
            if opt.name == 'size':
                logger.info(opt.values)
                self._size = opt.values[0].intValue
                
        logger.info('------------------------preprocessor_Start - UDF - Fields--------------------------------------')
        # logger.info(self._field,self._size)
        logger.info('------------------------preprocessor_End - UDF - Fields--------------------------------------')
        success = True
        msg = ''
        if self._size == '':
            success = False
            msg = 'must provide window size'
        response =udf_pb2.Response()
        response.init.success = success
        response.init.error = msg.encode()
        logger.info(response)
        return response
        

    def begin_batch(self, begin_req):
        # Do something at the beginning of the batch
        logger.info("************** preprocessor_Hello BEGIN BATCH********")
        response = udf_pb2.Response()
        response.begin.CopyFrom(begin_req)
        self._begin_response = response
        logger.info(response)
        logger.info("************** preprocessor_ByeBye BEGIN BATCH******")

    def snapshot(self):
        # Take a snapshot of the current data, if the task stops for some reason
        logger.info('preprocessor_snapshot trigger')
        data = {}
        for group, state in self._state.items():
            data[group] = state.snapshot()
        response = udf_pb2.Response()
        response.snapshot.snapshot = json.dumps(data).encode()
        #logger.info(data)
        return response

    def restore(self, restore_req):
        logger.info('----------------------------------preprocessor_Restore trigger----------------------------------')
        response = udf_pb2.Response()
        response.restore.success = True
        response.restore.error = ''
        return response


    def point(self,point):
        # process each point within the batch
        logger.info('************** preprocessor_Hello Point')
        #logger.info(point)
        logger.info('*******preprocessor_point content******')
        logger.info(str(len(point.fieldsDouble)))
        logger.info('********************** preprocessor_sensor fields with values ********************************')
        logger.info(point.fieldsDouble)
        sensorsPoint = point.fieldsDouble
        if len(sensorsPoint) == self._columnCount:
            self._pointerList.append(point)
            logger.info('******* preprocessor_pointer values loaded into list******')

        if len(self._pointerList) == self._size:
            logger.info('********** preprocessor_batch of '+ str(self._size)+' sensor data loaded***************')
            #sensorDf = pd.DataFrame(data=numpySensorValues, columns=self._sensorColumns)
            logger.info('preprocessor_starting fields doubles ')
            pre_processed_data = self.preprocess_sensorData()
            logger.info('preprocessor_preprocessed length of array ' + str(len(pre_processed_data)))
            pointIncNumber=0
            for p in self._pointerList:
                mappedFeildsDouble = self.map_preprocessed_sensordata(pre_processed_data[pointIncNumber])
                logger.info('preprocessor_mapped preprocessed fields doubles ')
                logger.info(mappedFeildsDouble)
                response = udf_pb2.Response()
                response.point.name = p.name
                response.point.time = p.time
                response.point.group = p.group
                response.point.tags.update(p.tags)
                response.point.fieldsDouble.update(mappedFeildsDouble)
                logger.info('**************** preprocessor_point response before writing**************')
                self._agent.write_response(response)
                pointIncNumber=pointIncNumber+1

            logger.info('**************** preprocessor_point response after writing************')
            self._pointerList=[]
            self._points=[]

        logger.info("************** preprocessor_ByeBye Point")
    
    def preprocess_sensorData(self):
        mainArray = []
        for point in self._pointerList:
            pointerValues=[]
            pointerSensors = point.fieldsDouble
            for col in self._sensorColumns:
                pointerValues.append(pointerSensors.get(col))
            mainArray.append(pointerValues)
        
        #Convert to numpy array 
        numpyMainArray = np.array(mainArray).astype(float)
        lstm_scaler = load(open('/tmp/kapacitor_udf/std_sclaer.pkl', 'rb'))
        scaledValues = lstm_scaler.transform(numpyMainArray)
        return scaledValues

    def map_preprocessed_sensordata(self,sensorValuesNumpy):
        fieldsDoubleObject={}
        incNumber=0
        for col in self._sensorColumns:
            fieldsDoubleObject[col] = sensorValuesNumpy[incNumber]
            incNumber=incNumber+1
        return fieldsDoubleObject
    
    def end_batch(self, end_req):
        # Do something at the end of the batch
        logger.info("************** preprocessor_Hello END BATCH")
        logger.info(end_req)
        logger.info("************** preprocessor_ByeBye END BATCH")

if __name__=='__main__':
    # Agent creation
    kapAgent =Agent()
    fddHandler=FddPredictorHandler(kapAgent)
    kapAgent.handler = fddHandler
    logger.info('preprocessor_Starting Agent for FddPredictorHandler')
    kapAgent.start()
    kapAgent.wait()
    logger.info('preprocessor_Agent Finished')



