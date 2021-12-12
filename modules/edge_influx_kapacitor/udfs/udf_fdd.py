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
        logger.info('__init__trigger')
        self._agent = agent
        self._field = ''
        self._size = 10
        self._points = []
        self._state = {}
        self._sensorColumns=["TWE_set","TEI","TWEI","TEO","TWEO","TCI","TWCI","TCO","TWCO","TSI","TSO","TBI","TBO","Cond Tons","Cooling Tons","Shared Cond Tons","Cond Energy Balance","Evap Tons"
    ,"Shared Evap Tons","Building Tons","Evap Energy Balance","kW","COP","kW_Ton","FWC","FWE","TEA","TCA","TRE","PRE","TRC","PRC","TRC_sub","T_suc","Tsh_suc","TR_dis","Tsh_dis","P_lift"
    ,"Amps","RLA%","Heat Balance%","Tolerance%","Unit Status","Active Fault","TO_sump","TO_feed","PO_feed","PO_net","TWCD","TWED","VSS","VSL","VH","VM","VC","VE","VW"
    ,"TWI","TWO","THI","THO","FWW","FWH","FWB"]
        self._columnCount = len(self._sensorColumns)

    def info(self):
        logger.info('info trigger')
        response = udf_pb2.Response()
        response.info.wants = udf_pb2.BATCH
        response.info.provides = udf_pb2.STREAM
        response.info.options['field'].valueTypes.append(udf_pb2.STRING)
        response.info.options['size'].valueTypes.append(udf_pb2.INT)
        logger.info(tf.__version__)
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
        #logger.info(point)
        logger.info('*******point content******')
        logger.info(str(len(point.fieldsDouble)))
        logger.info('********************** sensor fields with values ********************************')
        logger.info(point.fieldsDouble)
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

            logger.info('******* pointer values loaded into list******')

        if len(self._points) == self._size:
            logger.info('********** batch of '+ str(self._size)+' sensor data loaded***************')
            response = udf_pb2.Response()
            response.point.name = 'point test name'
            response.point.time = point.time
            response.point.group = 'point test group'
            response.point.fieldsString['fault'] = 'test fault'
            logger.info('**************** point response before writing**************')
            logger.info(response)
            self._agent.write_response(response)
            logger.info('**************** point response after writing************')
            
            #Convert list to numpy array 
            numpySensorValues = np.array(self._points)
            logger.info('************* sensor values convert into numpy ***********')
            #sensorDf = pd.DataFrame(data=numpySensorValues, columns=self._sensorColumns)
            self.predictDataCondition(numpySensorValues)
            self._points=[]
        logger.info("************** ByeBye Point")

    def predictDataCondition(self,numpySensorValues):
        fdd_model = tf.keras.models.load_model('/tmp/kapacitor_udf/model_new.h5',compile= False)
        lstm_scaler = load(open('/tmp/kapacitor_udf/std_sclaer.pkl', 'rb'))
        realDataArray=[[[ 2.88954095, -2.77214517, -2.45401974, -2.38537815,
         -1.93021891, -1.94129233,  0.36617625,  0.36673332,
          0.00824352,  0.02222923,  0.10669647, -1.88060275,
         -2.38503153, -2.42631201, -0.91702345, -0.92819163,
          1.70797402, -1.75797872, -1.02584421, -0.9126897 ,
         -0.79736741,  0.22194012, -0.00350149, -0.60004191,
         -0.00350006,  0.47967437, -1.81432843, -2.23193522,
         -1.04118189, -0.8675627 , -0.75888221, -0.34543812,
         -0.36494132, -1.12536187, -1.10757469, -1.49891928,
          0.524842  ,  0.78001796, -0.08313722, -0.64838344,
         -0.65346694, -0.00350098,  0.32666676,  0.18936017,
         -0.17121596, -0.44522381, -0.20584366,  0.02665603,
          0.22849573, -0.93785974, -0.69115654, -1.26959326,
         -0.42713511,  0.00350072, -1.10505649, -0.10020677,
         -2.46700561, -1.18761298, -0.57560857,  0.60441399,
         -2.31637639, -0.00350072, -0.89678137, -0.40036559,
          1.11864565],
        [ 2.89069617, -2.77214517, -2.44535611, -2.38537815,
         -1.92165255, -1.94129233,  0.36069265,  0.33964468,
          0.01310301,  0.01011941,  0.10669647, -1.8742049 ,
         -2.38503153, -2.42631201, -0.889138  , -0.87752624,
          1.68979004, -1.7381848 , -1.02543949, -0.92597178,
         -0.79716544,  0.13397846, -0.00350149, -0.60125444,
         -0.00350006,  0.44309677, -1.80887329, -1.99128901,
         -1.14526734, -0.8675627 , -0.75888221, -0.34543812,
         -0.3954605 , -0.96512152, -1.10757469, -1.29097   ,
          0.54520272,  0.78001796, -0.07293182, -0.64838344,
         -0.65346694, -0.00350113,  0.32666676,  0.18936017,
         -0.17121596, -0.41211127, -0.23633796, -0.14419764,
          0.08030599, -0.93785974, -0.75895592, -1.26959326,
         -0.42713511,  0.00350072, -1.10505649, -0.10020677,
         -2.46700561, -1.18761298, -0.55455969,  0.59855316,
         -2.31637639, -0.00350072, -0.88000644, -0.40021555,
          1.11109829],
        [ 2.89185138, -2.77214517, -2.44535611, -2.42816894,
         -1.92165255, -1.94129233,  0.36617625,  0.39382195,
          0.00824352,  0.01011941,  0.10669647, -1.8742049 ,
         -2.38503153, -2.41764008, -0.91595094, -0.92695589,
          1.70570102, -1.75589515, -1.02543949, -0.92597178,
         -0.73657382,  0.22223333, -0.00350149, -0.60064818,
         -0.00350006,  0.49186691, -1.80887329, -2.23193522,
         -1.04118189, -0.8675627 , -0.75888221, -0.31308291,
         -0.36494132, -1.0452417 , -1.1356862 , -1.49891928,
          0.524842  ,  0.75862034, -0.0474183 , -0.64838344,
         -0.65346694, -0.00350098,  0.32666676,  0.18936017,
         -0.17121596, -0.41211127, -0.20584366, -0.03029519,
          0.08030599, -0.93785974, -0.69115654, -1.26959326,
         -0.42713511,  0.00350072, -1.10505649, -0.10020677,
         -2.46700561, -1.00052534, -0.55455969,  0.59855316,
         -2.31005108, -0.00350072, -0.89446758, -0.29188846,
          1.12403662],
        [ 2.89300659, -2.77214517, -2.43669249, -2.38537815,
         -1.9130862 , -1.94129233,  0.36069265,  0.33964468,
          0.00824352,  0.02222923,  0.10669647, -1.8742049 ,
         -2.37617532, -2.41764008, -0.90308073, -0.93066312,
          1.69660903, -1.74339373, -1.03879514, -0.94058207,
         -0.80100291,  0.12782115, -0.00350148, -0.61944237,
         -0.00350003,  0.46341766, -1.91797603, -2.23193522,
         -0.97179159, -0.8675627 , -0.75888221, -0.2807277 ,
         -0.33442214, -1.07194842, -1.1356862 , -1.37414971,
          0.54520272,  0.75862034, -0.0372129 , -0.60042482,
         -0.60322971, -0.00350111,  0.28554065,  0.18936017,
         -0.17121596, -0.44522381, -0.20584366, -0.08724641,
          0.13587714, -0.90203611, -0.69115654, -1.26959326,
         -0.42713511,  0.00350072, -1.10505649, -0.10020677,
         -2.46700561, -1.18761298, -0.55455969,  0.59855316,
         -2.30372577, -0.00350072, -0.89562448, -0.4068172 ,
          1.11972385],
        [ 2.8941618 , -2.77214517, -2.43669249, -2.38537815,
         -1.92165255, -1.94129233,  0.36617625,  0.36673332,
          0.00824352,  0.01011941,  0.10669647, -1.86780705,
         -2.37617532, -2.40896815, -0.91523592, -0.92572015,
          1.70229153, -1.75276979, -1.02786779, -0.9286282 ,
         -0.74142115,  0.21460999, -0.00350144, -0.62611127,
         -0.00350002,  0.49593108, -1.9288863 , -2.08754749,
         -1.04118189, -0.94508749, -0.80878604, -0.31308291,
         -0.36494132, -0.96512152, -1.10757469, -1.29097   ,
          0.50448127,  0.73722272, -0.07293182, -0.64838344,
         -0.65346694, -0.00350096,  0.32666676,  0.18936017,
         -0.17121596, -0.44522381, -0.17534935, -0.03029519,
          0.15903179, -0.93785974, -0.69115654, -1.26959326,
         -0.42713511,  0.00350072, -1.10505649, -0.10020677,
         -2.46700561, -1.18761298, -0.57560857,  0.59855316,
         -2.30372577, -0.00350072, -0.89533525, -0.3004406 ,
          1.12511482],
        [ 2.89531701, -2.77214517, -2.43669249, -2.38537815,
         -1.92165255, -1.94129233,  0.36069265,  0.36673332,
          0.01310301,  0.02222923,  0.11176999, -1.86780705,
         -2.37617532, -2.40896815, -0.88449043, -0.92942738,
          1.70229153, -1.74339373, -1.013298  , -0.9126897 ,
         -0.73637185,  0.22223333, -0.00350144, -0.60852961,
         -0.00350005,  0.47967437, -1.80887329, -2.23193522,
         -1.07587704, -0.8675627 , -0.75888221, -0.31308291,
         -0.36494132, -1.07194842, -1.1356862 , -1.49891928,
          0.524842  ,  0.75862034, -0.0474183 , -0.60042482,
         -0.60322971, -0.00350106,  0.28554065,  0.18936017,
         -0.17121596, -0.44522381, -0.17534935, -0.11572203,
          0.1914483 , -0.90203611, -0.69115654, -1.26959326,
         -0.42713511,  0.00350072, -1.10505649, -0.10020677,
         -2.46700561, -1.18761298, -0.57560857,  0.59855316,
         -2.29740046, -0.00350072, -0.89620292, -0.29158838,
          1.11756746],
        [ 2.89647222, -2.77214517, -2.42586295, -2.42816894,
         -1.93021891, -1.94129233,  0.36617625,  0.36673332,
          0.01796249,  0.04644887,  0.11176999, -1.86780705,
         -2.3673191 , -2.40896815, -0.88127287, -0.86887605,
          1.70911052, -1.75381158, -1.00237065, -0.90073583,
         -0.80100291,  0.12811435, -0.00350144, -0.59458554,
         -0.00350007,  0.49999526, -1.91797603, -2.28006446,
         -0.93709644, -0.8675627 , -0.75888221, -0.24837249,
         -0.30390296, -0.96512152, -1.1356862 , -1.49891928,
          0.524842  ,  0.73722272, -0.07293182, -0.60042482,
         -0.60322971, -0.00350103,  0.28554065,  0.18936017,
         -0.17121596, -0.41211127, -0.17534935, -0.11572203,
          0.08030599, -0.83038883, -0.72505623, -2.12307235,
         -0.42713511,  0.00350072, -0.71741677, -0.10020677,
         -2.46700561, -1.06288788, -0.57560857,  0.59855316,
         -2.29740046, -0.00350072, -0.87856033, -0.4068172 ,
          1.12080204],
        [ 2.89762743, -3.14961868, -2.42586295, -2.38537815,
         -1.93878527, -1.96260251,  0.36617625,  0.36673332,
          0.01796249,  0.04644887,  0.11684351, -1.86780705,
         -2.3673191 , -2.40896815, -0.88699297, -0.93189886,
          1.70115503, -1.74235194, -0.98132539, -0.87771355,
         -0.79857924,  0.13192602, -0.00350144, -0.56972871,
         -0.00350011,  0.45935348, -1.84705925, -2.08754749,
         -0.97179159, -0.8675627 , -0.79215143, -0.31308291,
         -0.36494132, -0.96512152, -1.14974195, -1.37414971,
          0.524842  ,  0.73722272, -0.0474183 , -0.60042482,
         -0.60322971, -0.00350089,  0.28554065,  0.18936017,
         -0.17121596, -0.41211127, -0.20584366, -0.08724641,
          0.10346064, -0.75874156, -0.69115654, -2.12307235,
         -0.39282445,  0.00350072, -0.68414436, -0.10020677,
         -2.46700561, -1.06288788, -0.57560857,  0.59855316,
         -2.29740046, -0.00350072, -0.89678137, -0.40246612,
          1.10570732],
        [ 2.89878264, -3.14961868, -2.42586295, -2.38537815,
         -1.93021891, -1.94129233,  0.36069265,  0.23129014,
          0.02282197, -0.01410022,  0.12191702, -1.86780705,
         -2.3673191 , -2.40896815, -0.85767749, -0.93560608,
          1.69774553, -1.73089231, -0.99225273, -0.88966743,
         -0.7981753 ,  0.13251244, -0.00350133, -0.63823656,
         -0.0035    ,  0.43090423, -1.83614898, -2.03941825,
         -1.17996249, -0.94508749, -0.80878604, -0.37779333,
         -0.42597968, -1.28560223, -1.1356862 , -1.24938014,
          0.524842  ,  0.80141559, -0.13416425, -0.55246621,
         -0.55299248, -0.00350102,  0.24686983,  0.18936017,
         -0.17121596, -0.44522381, -0.17534935, -0.08724641,
          0.09882971, -0.61544701, -0.65725685, -2.12307235,
         -0.35848062,  0.00350072, -0.65054892, -0.10020677,
         -2.46700561, -1.06288788, -0.55455969,  0.60441399,
         -2.29740046, -0.00350072, -0.89793826, -0.40171593,
          1.10139454],
        [ 2.89993785, -3.14961868, -2.42586295, -2.32119197,
         -1.93878527, -2.00522288,  0.32642011,  0.19065719,
          0.01310301, -0.07464931,  0.12191702, -1.84221563,
         -2.34960668, -2.38295236, -0.78689135, -1.04435132,
          1.68751705, -1.69130447, -0.98537255, -0.85557675,
         -0.73940143,  0.39287895, -0.00350138, -0.60489203,
         -0.00350006,  0.46748184, -1.87433493, -2.28006446,
         -1.00648674, -0.92570629, -0.79215143, -0.37779333,
         -0.42597968, -1.20548205, -1.14974195, -1.41573956,
          0.50448127,  0.75862034, -0.11375344, -0.50450759,
         -0.50275525, -0.0035014 ,  0.20850592,  0.18936017,
         -0.17121596, -0.41211127, -0.20584366, -0.03029519,
          0.16829365, -0.72291792, -0.4538587 , -2.12307235,
         -0.32416997,  0.00350072, -0.61727651, -0.10020677,
         -2.46700561, -1.06288788, -0.55455969,  0.60441399,
         -2.29740046, -0.00350072, -0.92975277, -0.2968397 ,
          1.10139454]]]
        logger.info('models and sclaer loaded')
        scaledValues = lstm_scaler.transform(numpySensorValues)
        reshapedSensorValues = scaledValues.reshape(-1,self._size,self._columnCount)
        logger.info(reshapedSensorValues)
        #numpyArray = np.array(realDataArray)
        logger.info('shape of numpy array is '+str(reshapedSensorValues.shape))
        prediction = fdd_model.predict(reshapedSensorValues).argmax(-1)[-1,-1]
        logger.info('The model prediction is '+str(prediction))
    
    
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



