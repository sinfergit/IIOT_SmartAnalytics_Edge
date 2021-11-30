from kapacitor.udf.agent import Agent, Handler
from kapacitor.udf import udf_pb2
import logging
import json

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger()

class FddPredictorHandler(Handler):
    def __init__(self,agent):
        # Define what your UDF wants and what will it provides and options
        logger.info('__init__trigger')
        self.__agent = agent
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
        return response

    def init(self,init_req):
        # Define what your UDF expects as options when parsing TICKScript
        logger.info('INIT trigger')
        for opt in init_req.options:
            if opt.name == 'field':
                self._field = opt.values[0].stringValue

        success = True
        msg = ''
        if self._field == '':
            success = False
            msg = 'A field name must be provided'
        response =udf_pb2.Response()
        response.init.success = success
        response.init.error = msg.encode()
        return response
        

    def begin_batch(self):
        # Do something at the beginning of the batch
        logger.info('begin_batch trigger')

    # def snapshot(self):
    #     # Take a snapshot of the current data, if the task stops for some reason
    #     logger.info('snapshot trigger')
    #     data = {}
    #     for group, state in self._state.items():
    #         data[group] = state.snapshot()
    #     response = udf_pb2.Response()
    #     response.snapshot.snapshot = json.dumps(data).encode()
    #     return response

    def point(self,point):
        # process each point within the batch
        logger.info('point trigger')
        logger.info(point)
        self._points.append(point)
        if len(self._points) == self._size:
            response = udf_pb2.Response()
            response.point.name = 'point test name'
            response.point.time = 'point test time'
            response.point.group = 'point test group'
            response.point.fieldsString['fault'] = 'test fault'
            self._agent.write_response(response)
            self._points.pop(0)
        pass
    
    def end_batch(self):
        # Do something at the end of the batch
        logger.info('end_batch')

if __name__=='__main__':
    # Agent creation
    kapAgent =Agent()
    fddHandler=FddPredictorHandler(kapAgent)
    kapAgent.handler = fddHandler
    logger.info('Starting Agent for FddPredictorHandler')
    kapAgent.start()
    kapAgent.wait()
    logger.info('Agent Finished')


