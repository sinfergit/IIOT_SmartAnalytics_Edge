from kapacitor.udf.agent import Agent, Handler
from kapacitor.udf import udf_pb2
from tensorflow.keras.layers import LSTM, Dense
import json
import logging

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger()

class FddPredictorHandler(Handler):
    def __init__(self,agent):
        # Define what your UDF wants and what will it provides and options
        logger.info('__init__trigger')
        self._agent = agent
        self._field = ''
        self._size = 10
        self._points = []
        self._state = {}

    def info(self):
        logger.info('info trigger')
        response = udf_pb2.Response()
        response.info.wants = udf_pb2.BATCH
        response.info.provides = udf_pb2.STREAM
        response.info.options['field'].valueTypes.append(udf_pb2.STRING)
        response.info.options['size'].valueTypes.append(udf_pb2.INT)
        return response

    def init(self,init_req):
        # Define what your UDF expects as options when parsing TICKScript
        logger.info('INIT trigger')
        for opt in init_req.options:
            if opt.name == 'field':
                logger.info(opt.values)
                self._field = opt.values[0].stringValue
            elif opt.name == 'size':
                logger.info(opt.values)
                self._size = opt.values[0].intValue
                
        logger.info('------------------------Start - UDF - Fields--------------------------------------')
        # logger.info(self._field,self._size)
        logger.info('------------------------End - UDF - Fields--------------------------------------')
        success = True
        msg = ''
        if self._field == '':
            success = False
            msg = 'must provide field name'
        response =udf_pb2.Response()
        response.init.success = success
        response.init.error = msg.encode()
        logger.info(response)
        return response
        

    def begin_batch(self, begin_req):
        # Do something at the beginning of the batch
        logger.info("************** Hello BEGIN BATCH********")
        response = udf_pb2.Response()
        response.begin.CopyFrom(begin_req)
        self._begin_response = response
        logger.info(begin_req)
        logger.info("************** ByeBye BEGIN BATCH******")

    def snapshot(self):
        # Take a snapshot of the current data, if the task stops for some reason
        logger.info('snapshot trigger')
        data = {}
        for group, state in self._state.items():
            data[group] = state.snapshot()
        response = udf_pb2.Response()
        response.snapshot.snapshot = json.dumps(data).encode()
        #logger.info(data)
        return response

    def restore(self, restore_req):
        logger.info('----------------------------------Restore trigger----------------------------------')
        response = udf_pb2.Response()
        response.restore.success = True
        response.restore.error = ''
        return response


    def point(self,point):
        # process each point within the batch
        logger.info('************** Hello Point')
        logger.info(point)
        self._points.append(point)
        if len(self._points) == self._size:
            response = udf_pb2.Response()
            response.point.name = 'point test name'
            response.point.time = point.time
            response.point.group = 'point test group'
            response.point.fieldsString['fault'] = 'test fault'
            logger.info('**************** point response **************')
            logger.info(response)
            self._agent.write_response(response)
            logger.info('**************** point response after writing************')
            self._points.pop(0)
        logger.info("************** ByeBye Point")

        
    
    def end_batch(self, end_req):
        # Do something at the end of the batch
        logger.info("************** Hello END BATCH")
        logger.info(end_req)
        logger.info("************** ByeBye END BATCH")

if __name__=='__main__':
    # Agent creation
    kapAgent =Agent()
    fddHandler=FddPredictorHandler(kapAgent)
    kapAgent.handler = fddHandler
    logger.info('Starting Agent for FddPredictorHandler')
    kapAgent.start()
    kapAgent.wait()
    logger.info('Agent Finished')



