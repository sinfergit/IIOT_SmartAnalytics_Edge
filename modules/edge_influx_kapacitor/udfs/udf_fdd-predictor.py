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
        logger.info('predictor__init__trigger')
        self._agent = agent
        self._size = 10
        self._points = []
        self._state = {}
        self._sensorColumns=["TWE_set","TEI","TWEI","TEO","TWEO","TCI","TWCI","TCO","TWCO","TSI","TSO","TBI","TBO",
     "kW","FWC","FWE","TEA","TCA","TRE","PRE","TRC","PRC","TRC_sub","T_suc","Tsh_suc","TR_dis","Tsh_dis","P_lift"
    ,"Amps","RLA%","Unit Status","Active Fault","TO_sump","TO_feed","PO_feed","PO_net","TWCD","TWED","VSS","VSL","VH","VM","VC","VE","VW"
    ,"TWI","TWO","THI","THO"]
        self._chillerConditions=["cf","eo","fwc","fwe","nc","normal","rl","ro"]
        self._columnCount = len(self._sensorColumns)

    def info(self):
        logger.info('predictor_info trigger')
        response = udf_pb2.Response()
        response.info.wants = udf_pb2.STREAM
        response.info.provides = udf_pb2.STREAM
        response.info.options['size'].valueTypes.append(udf_pb2.INT)
        logger.info(tf.__version__)
        return response

    def init(self,init_req):
        # Define what your UDF expects as options when parsing TICKScript
        logger.info('predictor_INIT trigger')
        for opt in init_req.options:
            if opt.name == 'size':
                logger.info(opt.values)
                self._size = opt.values[0].intValue
                
        logger.info('------------------------predictor_Start - UDF - Fields--------------------------------------')
        # logger.info(self._field,self._size)
        logger.info('------------------------predictor_End - UDF - Fields--------------------------------------')
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
        logger.info("************** predictor_Hello BEGIN BATCH********")
        response = udf_pb2.Response()
        response.begin.CopyFrom(begin_req)
        self._begin_response = response
        logger.info(response)
        logger.info("************** predictor_ByeBye BEGIN BATCH******")

    def snapshot(self):
        # Take a snapshot of the current data, if the task stops for some reason
        logger.info('predictor_snapshot trigger')
        data = {}
        for group, state in self._state.items():
            data[group] = state.snapshot()
        response = udf_pb2.Response()
        response.snapshot.snapshot = json.dumps(data).encode()
        #logger.info(data)
        return response

    def restore(self, restore_req):
        logger.info('----------------------------------predictor_Restore trigger----------------------------------')
        response = udf_pb2.Response()
        response.restore.success = True
        response.restore.error = ''
        return response


    def point(self,point):
        # process each point within the batch
        logger.info('************** predictor_Hello Point from predictor')
        #logger.info(point)
        logger.info('*******predictor_point content******')
        logger.info(str(len(point.fieldsDouble)))
        logger.info('********************** predictor_sensor fields with values ********************************')
        logger.info(point)
        #logger.info(point.fieldsDouble)
        sensorsPoint = point.fieldsDouble
        if len(sensorsPoint) == self._columnCount:
            pointerValues = []
            #Mapping of the unordered fields into ordered
            for col in self._sensorColumns:
             pointerValues.append(
                 sensorsPoint.get(col)
             )

            #Reversing the sensor data points 
            # pointerValues.reverse()
            # logger.info('********************reversed sensor values*******************')
            # logger.info(pointerValues)
            # pointerKeys = [val for val in sensorsPoint]
            # pointerKeys.reverse()
            # logger.info('********************reversed sensor names*******************')
            # logger.info(pointerKeys) 
            self._points.append(pointerValues)

            logger.info('******* predictor_pointer values loaded into list******')

        if len(self._points) == self._size:
            logger.info('********** predictor_batch of '+ str(self._size)+' sensor data loaded***************')
            response = udf_pb2.Response()
            #Convert list to numpy array 
            numpySensorValues = np.array(self._points)
            logger.info('************* predictor_sensor values convert into numpy ***********')
            #sensorDf = pd.DataFrame(data=numpySensorValues, columns=self._sensorColumns)
            conditionId = self.predictDataCondition(numpySensorValues)
            response.point.name = point.name
            response.point.time = point.time
            response.point.group = point.group
            response.point.fieldsInt['conditionId'] = conditionId
            response.point.fieldsString['conditionName'] = self._chillerConditions[conditionId]
            logger.info('**************** predictor_point response before writing**************')
            logger.info(response)
            self._agent.write_response(response)
            logger.info('**************** predictor_point response after writing************')
            
            logger.info('predictor_sensor pointer values check ')
            logger.info(self._points)
            
            self._points=[]

        logger.info("************** predictor_ByeBye Point")

    def predictDataCondition(self,numpySensorValues):
        fdd_model = tf.keras.models.load_model('/tmp/kapacitor_udf/model_new.h5',compile= False)
        logger.info('predictor_inside the prediction function')
        #logger.info(numpySensorValues)
        logger.info('predictor_models and sclaer loaded')
        reshapedSensorValues = numpySensorValues.reshape(-1,self._size,self._columnCount)
        #logger.info(reshapedSensorValues)
        #numpyArray = np.array(realDataArray)
        
        logger.info('predictor_predictor_shape of numpy array is '+str(reshapedSensorValues.shape))
        prediction = fdd_model.predict(reshapedSensorValues).argmax(-1)[-1,-1]
        logger.info('predictor_The model prediction is '+str(prediction))
        return prediction
    
    def end_batch(self, end_req):
        # Do something at the end of the batch
        logger.info("************** predictor_Hello END BATCH")
        logger.info(end_req)
        logger.info("************** predictor_ByeBye END BATCH")

if __name__=='__main__':
    # Agent creation
    kapAgent =Agent()
    fddHandler=FddPredictorHandler(kapAgent)
    kapAgent.handler = fddHandler
    logger.info('predictor_Starting Agent for NewFddPredictorHandler')
    kapAgent.start()
    kapAgent.wait()
    logger.info('predictor_Agent Finished')



