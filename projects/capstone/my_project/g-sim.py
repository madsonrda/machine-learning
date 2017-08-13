import simpy
import random
import functools
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sys
import argparse
import logging
from sklearn import linear_model
from sklearn.metrics import mean_squared_error as mse
from sklearn.multioutput import MultiOutputRegressor
import os, errno

#Parsing the inputs arguments
parser = argparse.ArgumentParser(description="Long Reach PON Simulator")
group = parser.add_mutually_exclusive_group()
group.add_argument("-q", "--quiet", action="store_true")
parser.add_argument("A", type=str, default='ipact',choices=["ipact","pd_dba"], help="DBA algorithm")
parser.add_argument("-O", "--onu", type=int, default=3, help="The number of ONUs")
parser.add_argument("-b", "--bucket", type=int, default=27000, help="The size of the ONU sender bucket in bytes")
parser.add_argument("-Q", "--qlimit", type=int, default=None ,help="The size of the ONU port queue in bytes")
parser.add_argument("-m", "--maxgrant", type=float, default=0, help="The maximum size of buffer which a grant can allow")
parser.add_argument("-d","--distance", type=int, default=100, nargs='?', help="Distance in km from ONU to OLT")
parser.add_argument("-e","--exponent", type=int, default=2320, nargs='?', help="Packet arrivals distribution exponent")
parser.add_argument("-s","--seed", type=int, default=20, help="Random seed")
parser.add_argument("-w","--window", type=int, default=20, help="PD-DBA window")
parser.add_argument("-p","--predict", type=int, default=20, help="PD-DBA predictions")
parser.add_argument("-o", "--output", type=str, default=None, help="Output file name")
args = parser.parse_args()

#Arguments
DBA_ALGORITHM = args.A
NUMBER_OF_ONUs= args.onu
DISTANCE = args.distance
MAX_GRANT_SIZE = args.maxgrant
MAX_BUCKET_SIZE = args.bucket
ONU_QUEUE_LIMIT = args.qlimit
EXPONENT = args.exponent
FILENAME = args.output
RANDOM_SEED = args.seed
WINDOW = args.window
PREDICT = args.predict



#settings
SIM_DURATION = 30
PKT_SIZE = 9000
MAC_TABLE = {}
Grant_ONU_counter = {}

#create directories
try:
    os.makedirs('csv/delay')
except OSError as e:
    if e.errno != errno.EEXIST:
        raise

try:
    os.makedirs('csv/grant_time')
except OSError as e:
    if e.errno != errno.EEXIST:
        raise
try:
    os.makedirs("csv/pkt")
except OSError as e:
    if e.errno != errno.EEXIST:
        raise

#logging
logging.basicConfig(filename='g-sim.log',level=logging.DEBUG,format='%(asctime)s %(message)s')
if FILENAME:
    delay_file = open("{}-delay.csv".format(FILENAME),"w")
    grant_time_file = open("{}-grant_time.csv".format(FILENAME),"w")
    pkt_file = open("{}-pkt.csv".format(FILENAME),"w")
elif DBA_ALGORITHM == "pd_dba":
    delay_file = open("csv/delay/{}-{}-{}-{}-{}-{}-{}-{}-{}-delay.csv".format(DBA_ALGORITHM,NUMBER_OF_ONUs,MAX_BUCKET_SIZE,MAX_GRANT_SIZE,DISTANCE,RANDOM_SEED,EXPONENT,WINDOW,PREDICT),"w")
    grant_time_file = open("csv/grant_time/{}-{}-{}-{}-{}-{}-{}-{}-{}-grant_time.csv".format(DBA_ALGORITHM,NUMBER_OF_ONUs,MAX_BUCKET_SIZE,MAX_GRANT_SIZE,DISTANCE,RANDOM_SEED,EXPONENT,WINDOW,PREDICT),"w")
    pkt_file = open("csv/pkt/{}-{}-{}-{}-{}-{}-{}-{}-{}-grant_time.csv".format(DBA_ALGORITHM,NUMBER_OF_ONUs,MAX_BUCKET_SIZE,MAX_GRANT_SIZE,DISTANCE,RANDOM_SEED,EXPONENT,WINDOW,PREDICT),"w")
else:
    delay_file = open("csv/delay/{}-{}-{}-{}-{}-{}-{}-delay.csv".format(DBA_ALGORITHM,NUMBER_OF_ONUs,MAX_BUCKET_SIZE,MAX_GRANT_SIZE,DISTANCE,RANDOM_SEED,EXPONENT),"w")
    grant_time_file = open("csv/grant_time/{}-{}-{}-{}-{}-{}-{}-grant_time.csv".format(DBA_ALGORITHM,NUMBER_OF_ONUs,MAX_BUCKET_SIZE,MAX_GRANT_SIZE,DISTANCE,RANDOM_SEED,EXPONENT),"w")
    pkt_file = open("csv/pkt/{}-{}-{}-{}-{}-{}-{}-pkt.csv".format(DBA_ALGORITHM,NUMBER_OF_ONUs,MAX_BUCKET_SIZE,MAX_GRANT_SIZE,DISTANCE,RANDOM_SEED,EXPONENT),"w")

delay_file.write("ONU_id,delay\n")
grant_time_file.write("source address,destination address,opcode,timestamp,counter,ONU_id,start,end\n")
pkt_file.write("size\n")

mse_file = open("csv/{}-{}-{}-{}-{}-{}-{}-mse.csv".format(DBA_ALGORITHM,NUMBER_OF_ONUs,MAX_BUCKET_SIZE,MAX_GRANT_SIZE,DISTANCE,RANDOM_SEED,EXPONENT),"w")
mse_file.write("mse_start,mse_end\n")

class ODN(object):
    """This class represents optical distribution Network."""
    def __init__(self, env):
        self.env = env
        self.upstream = simpy.Store(env) # upstream chanel
        self.downstream = [] # downstream chanel
        #create downstream splitter
        for i in range(NUMBER_OF_ONUs):
            self.downstream.append(simpy.Store(env))

    def up_latency(self, value,delay):
        """Calculates upstream propagation delay."""
        yield self.env.timeout(delay)
        self.upstream.put(value)

    def down_latency(self,ONU,value):
        """Calculates downstream propagation delay."""
        yield self.env.timeout(ONU.delay)
        self.downstream[ONU.oid].put(value)

    def put_request(self, value,delay):
        """ONU Puts the Request message in the upstream """
        self.env.process(self.up_latency(value,delay))

    def get_request(self):
        """OLT gets the Request message from upstream  """
        return self.upstream.get()

    def put_grant(self,ONU,value):
        """OLT Puts the Grant message in the downstream """
        self.env.process(self.down_latency(ONU,value))

    def get_grant(self,ONU_id):
        """ONU gets the Grant message from downstream """
        return self.downstream[ONU_id].get()


class Packet(object):
    """ This class represents a network packet """

    def __init__(self, time, size, id, src="a", dst="z"):
        self.time = time# creation time
        self.size = size # packet size
        self.id = id # packet id
        self.src = src #packet source address
        self.dst = dst #packet destination address

    def __repr__(self):
        return "id: {}, src: {}, time: {}, size: {}".\
            format(self.id, self.src, self.time, self.size)

class PacketGenerator(object):
    """This class represents the packet generation process """
    def __init__(self, env, id,  adist, sdist, fix_pkt_size=None, finish=float("inf")):
        self.id = id # packet id
        self.env = env # Simpy Environment
        self.arrivals_dist = adist #packet arrivals distribution
        self.size_dist = sdist #packet size distribution

        self.fix_pkt_size = fix_pkt_size # Fixed packet size
        self.finish = finish # packe end time
        self.out = None # packet generator output
        self.packets_sent = 0 # packet counter
        self.action = env.process(self.run())  # starts the run() method as a SimPy process

    def run(self):
        """The generator function used in simulations.
        """
        while self.env.now < self.finish:
            # wait for next transmission
            yield self.env.timeout(self.arrivals_dist())
            self.packets_sent += 1


            if self.fix_pkt_size:
                p = Packet(self.env.now, self.fix_pkt_size, self.packets_sent, src=self.id)
                pkt_file.write("{}\n".format(self.fix_pkt_size))
            else:
                size = self.size_dist()
                p = Packet(self.env.now, size, self.packets_sent, src=self.id)
                pkt_file.write("{}\n".format(size))
            self.out.put(p) # put the packet in ONU port

class ONUPort(object):

    def __init__(self, env, qlimit=None):
        self.buffer = simpy.Store(env)#buffer
        self.grant_real_usage = simpy.Store(env) # Used in grant prediction report
        self.grant_size = 0
        self.grant_final_time = 0
        self.guard_interval = 0.000001
        self.env = env
        self.out = None # ONU port output
        self.packets_rec = 0 #received pkt counter
        self.packets_drop = 0#dropped pkt counter
        self.qlimit = qlimit #Buffer queue limit
        self.byte_size = 0  # Current size of the buffer in bytes
        self.last_buffer_size = 0 # size of the last buffer request
        self.busy = 0  # Used to track if a packet is currently being sent
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.pkt = None #network packet obj
        self.grant_loop = False #flag if grant time is being used

    def set_grant(self,grant): #setting grant byte size and its ending
        self.grant_size = grant['grant_size']
        self.grant_final_time = grant['grant_final_time']

    def update_last_buffer_size(self,requested_buffer): #update the size of the last buffer request
        self.last_buffer_size = requested_buffer

    def get_last_buffer_size(self): #return the size of the last buffer request
        return self.last_buffer_size

    def get_pkt(self):
        """process to get the packet from the buffer   """

        try:
            pkt = (yield self.buffer.get() )#getting a packet from the buffer
            self.pkt = pkt

        except simpy.Interrupt as i:
            logging.debug("Error while getting a packet from the buffer ({})".format(i))

            pass

        if not self.grant_loop:#put the pkt back to the buffer if the grant time expired

            self.buffer.put(pkt)



    def send(self,ONU_id):
        """ process to send pkts
        """
        self.grant_loop = True #flag if grant time is being used
        start_grant_usage = None #grant timestamp
        end_grant_usage = 0 #grant timestamp

        while self.grant_final_time > self.env.now:

            get_pkt = self.env.process(self.get_pkt())#trying to get a package in the buffer
            grant_timeout = self.env.timeout(self.grant_final_time - self.env.now)
            yield get_pkt | grant_timeout#wait for a package to be sent or the grant timeout

            if (self.grant_final_time <= self.env.now):
                #The grant time has expired
                break
            if self.pkt is not None:
                pkt = self.pkt
                if not start_grant_usage:
                    start_grant_usage = self.env.now #initialized the real grant usage time
                start_pkt_usage = self.env.now ##initialized the pkt usage time

            else:
                #there is no pkt to be sent
                logging.debug("{}: there is no packet to be sent".format(self.env.now))
                break
            self.busy = 1
            self.byte_size -= pkt.size
            if self.byte_size < 0:#Prevent the buffer from being negative
                logging.debug("{}: Negative buffer".format(self.env.now))
                self.byte_size += pkt.size
                self.buffer.put(pkt)
                break

            bits = pkt.size * 8
            sending_time = 	bits/float(1000000000) # buffer transmission time

            #To avoid fragmentation by passing the Grant window
            if env.now + sending_time > self.grant_final_time + self.guard_interval:
                self.byte_size += pkt.size

                self.buffer.put(pkt)
                break

            #write the pkt transmission delay
            delay_file.write( "{},{}\n".format( ONU_id, (self.env.now - pkt.time) ) )
            yield self.env.timeout(sending_time)

            end_pkt_usage = self.env.now
            end_grant_usage += end_pkt_usage - start_pkt_usage

            self.pkt = None

        #ending of the grant
        self.grant_loop = False #flag if grant time is being used
        if start_grant_usage:# if any pkt has been sent
            #send the real grant usage
            self.grant_real_usage.put( [start_grant_usage , start_grant_usage + end_grant_usage] )
        else:
            #logging.debug("buffer_size:{}, grant duration:{}".format(b,grant_timeout))
            self.grant_real_usage.put([])# send a empty list



    def run(self): #run the port as a simpy process
        while True:
            yield self.env.timeout(5)


    def put(self, pkt):
        """receives a packet from the packet genarator and put it on the queue
            if the queue is not full, otherwise drop it.
        """

        self.packets_rec += 1
        tmp = self.byte_size + pkt.size
        if self.qlimit is None: #checks if the queue size is unlimited
            self.byte_size = tmp
            return self.buffer.put(pkt)
        if tmp >= self.qlimit: # chcks if the queue is full
            self.packets_drop += 1
            #return
        else:
            self.byte_size = tmp
            self.buffer.put(pkt)

class ONU(object):
    def __init__(self,distance,oid,env,odn,exp,qlimit,fix_pkt_size,bucket):
        self.env = env
        self.grant_report_store = simpy.Store(self.env) #Simpy Stores grant usage report
        self.grant_report = []
        self.distance = distance #fiber distance
        self.oid = oid #ONU indentifier
        self.delay = self.distance/ float(210000) # fiber propagation delay
        self.excess = 0 #difference between the size of the request and the grant
        arrivals_dist = functools.partial(random.expovariate, exp) #packet arrival distribuition
        size_dist = functools.partial(random.expovariate, 0.1)  # packet size distribuition, mean size 100 bytes
        self.pg = PacketGenerator(self.env, "bbmp", arrivals_dist, size_dist,fix_pkt_size) #creates the packet generator
        if qlimit == 0:# checks if the queue has a size limit
            queue_limit = None
        else:
            queue_limit = qlimit
        self.port = ONUPort(self.env, qlimit=queue_limit)#create ONU PORT
        self.pg.out = self.port #forward packet generator output to ONU port
        self.sender = self.env.process(self.ONU_sender(odn))
        self.receiver = self.env.process(self.ONU_receiver(odn))
        self.bucket = bucket #Bucket size


    def ONU_receiver(self,odn):
        while True:
            # Grant stage
            grant = yield odn.get_grant(self.oid)#waiting for a grant
            pred_grant_usage_report = [] # grant prediction report list
            # real start and endtime used report to OLT

            self.excess = self.port.get_last_buffer_size() - grant['grant_size'] #update the excess
            self.port.set_grant(grant) #grant info to onu port

            sent_pkt = self.env.process(self.port.send(self.oid)) # send pkts during grant time
            yield sent_pkt # wait grant be used
            grant_usage = yield self.port.grant_real_usage.get() # get grant real utilisation
            if len(grant_usage) == 0: #debug
                logging.debug("Error in grant_usage")
            #yield self.env.timeout(self.delay)

            # Prediction stage
            if grant['prediction']:#check if have any predicion in the grant
                for pred in grant['prediction']:
                    # construct grant pkt
                    pred_grant = {'grant_size': grant['grant_size'], 'grant_final_time': pred[1]}
                    #wait next cycle
                    try:
                        next_grant = pred[0] - self.env.now #time until next grant begining
                        yield self.env.timeout(next_grant)  #wait for the next grant
                    except Exception as e:
                        logging.debug("{}: pred {}, gf {}".format(self.env.now,pred,grant['grant_final_time']))
                        logging.debug("Error while waiting for the next grant ({})".format(e))
                        break

                    self.port.set_grant(pred_grant) #grant info to onu port
                    sent_pkt = self.env.process(self.port.send(self.oid))#sending predicted messages

                    yield sent_pkt # wait grant be used
                    grant_usage = yield self.port.grant_real_usage.get() # get grant real utilisation
                    yield self.env.timeout(self.delay) # wait grant propagation delay
                    if len(grant_usage) > 0: # filling grant prediction report list
                        pred_grant_usage_report.append(grant_usage)
                        #logging.debug("{}:pred={},usage={}".format(self.env.now,pred,grant_usage))
                    else:
                        logging.debug("{}:Erro in pred_grant_usage".format(self.env.now))
                        break
            # grant mean squared errors
            if len(pred_grant_usage_report) > 0 and len(pred_grant_usage_report) == len(grant['prediction']):
                mse_start = mse(np.array(pred_grant_usage_report)[:,0],np.array(grant['prediction'])[:,0])
                mse_end = mse(np.array(pred_grant_usage_report)[:,1],np.array(grant['prediction'])[:,1])
                mse_file.write("{},{}\n".format(mse_start,mse_end))
            yield self.env.timeout(self.delay) # propagation delay

            #Signals the end of grant processing to allow new requests
            yield self.grant_report_store.put(pred_grant_usage_report)

    def ONU_sender(self, odn):
        """A process which checks the queue size and send a REQUEST message to OLT"""
        while True:
            # send a REQUEST only if the queue size is greater than the bucket size
            if self.port.byte_size >= self.bucket:
                requested_buffer = self.port.byte_size #gets the size of the buffer that will be requested
                #update the size of the current/last buffer REQUEST
                self.port.update_last_buffer_size(requested_buffer)
                # creating request message
                msg = {'text':"ONU %s sent this REQUEST for %.6f at %f" %
                    (self.oid,self.port.byte_size, self.env.now),'buffer_size':requested_buffer,'ONU':self}
                odn.put_request((msg),self.delay)# put the request message in the odn

                # Wait for the grant processing to send the next request
                self.grant_report = yield self.grant_report_store.get()
            else: # periodic check delay
                yield self.env.timeout(self.delay)

class DBA(object):
    """DBA Parent class, heritated by every kind of DBA"""
    def __init__(self,env,max_grant_size,grant_store):
        self.env = env
        self.max_grant_size = max_grant_size
        self.grant_store = grant_store
        self.guard_interval = 0.000001

class IPACT(DBA):
    def __init__(self,env,max_grant_size,grant_store):
        DBA.__init__(self,env,max_grant_size,grant_store)
        self.counter = simpy.Resource(self.env, capacity=1)#create a queue of requests to DBA


    def dba(self,ONU,buffer_size):
        with self.counter.request() as my_turn:
            """ DBA only process one request at a time """
            yield my_turn
            time_stamp = self.env.now # timestamp dba starts processing the request
            delay = ONU.delay # oneway delay

            # check if max grant size is enabled
            if self.max_grant_size > 0 and buffer_size > self.max_grant_size:
                buffer_size = self.max_grant_size
            bits = buffer_size * 8
            sending_time = 	bits/float(1000000000) #buffer transmission time
            grant_time = delay + sending_time
            grant_final_time = self.env.now + grant_time # timestamp for grant end
            counter = Grant_ONU_counter[ONU.oid] # Grant message counter per ONU
            # write grant log
            grant_time_file.write( "{},{},{},{},{},{},{},{}\n".format(MAC_TABLE['olt'], MAC_TABLE[ONU.oid],"02", time_stamp,counter, ONU.oid,self.env.now,grant_final_time) )
            # construct grant message
            grant = {'ONU':ONU,'grant_size': buffer_size, 'grant_final_time': grant_final_time, 'prediction': None}
            self.grant_store.put(grant) # send grant to OLT
            Grant_ONU_counter[ONU.oid] += 1

            # timeout until the end of grant to then get next grant request
            yield self.env.timeout(delay+grant_time + self.guard_interval)


class PD_DBA(DBA):
    def __init__(self,env,max_grant_size,grant_store,window=20,predict=5):
        DBA.__init__(self,env,max_grant_size,grant_store)
        self.counter = simpy.Resource(self.env, capacity=1)#create a queue of requests to DBA
        self.window = window    # past observations window size
        self.predict = predict # number of predictions
        self.grant_history = range(NUMBER_OF_ONUs) #grant history per ONU (training set)
        for i in range(NUMBER_OF_ONUs):
            # training unit
            self.grant_history[i] = {'counter': [], 'start': [], 'end': []}
        ##----- Prediction model--------
        # Uncomment the lines below to change the prediction model
        #model = linear_model.LinearRegression()
        # Comment either the line above OR the line below
        model = linear_model.Ridge(alpha=.5)
        ##------------------------------
        self.model = MultiOutputRegressor(model)


    def predictor(self, ONU_id):
        # check if there's enough observations to fill window

        if len( self.grant_history[ONU_id]['start'] ) >= self.window :
            #reduce the grant history to the window size
            self.grant_history[ONU_id]['start'] = self.grant_history[ONU_id]['start'][-self.window:]
            self.grant_history[ONU_id]['end'] = self.grant_history[ONU_id]['end'][-self.window:]
            self.grant_history[ONU_id]['counter'] = self.grant_history[ONU_id]['counter'][-self.window:]
            df_tmp = pd.DataFrame(self.grant_history[ONU_id]) # temp dataframe w/ past grants
            # create a list of the next p Grants that will be predicted
            X_pred = np.arange(self.grant_history[ONU_id]['counter'][-1] +1, self.grant_history[ONU_id]['counter'][-1] + 1 + self.predict).reshape(-1,1)

            # model fitting
            self.model.fit( np.array( df_tmp['counter'] ).reshape(-1,1) , df_tmp[['start','end']] )
            pred = self.model.predict(X_pred) # predicting start and end

            predictions = list(pred)

            return predictions

        else:
            return  None


    def dba(self,ONU,buffer_size):
        with self.counter.request() as my_turn:
            """ DBA only process one request at a time """
            yield my_turn
            time_stamp = self.env.now
            delay = ONU.delay

            if len(ONU.grant_report) > 0:
                # if predictions where utilized, update history with real grant usage
                for report in ONU.grant_report:
                    self.grant_history[ONU.oid]['start'].append(report[0])
                    self.grant_history[ONU.oid]['end'].append(report[1])
                    self.grant_history[ONU.oid]['counter'].append( self.grant_history[ONU.oid]['counter'][-1] + 1  )

            # check if max grant size is enabled
            if self.max_grant_size > 0 and buffer_size > self.max_grant_size:
                buffer_size = self.max_grant_size
            bits = buffer_size * 8
            sending_time = 	bits/float(1000000000) #buffer transmission time
            grant_time = delay + sending_time # one way delay + transmission time
            grant_final_time = self.env.now + grant_time # timestamp for grant end

            # Update grant history with grant requested
            self.grant_history[ONU.oid]['start'].append(self.env.now)
            self.grant_history[ONU.oid]['end'].append(grant_final_time)
            if len(self.grant_history[ONU.oid]['counter']) > 0:
                self.grant_history[ONU.oid]['counter'].append( self.grant_history[ONU.oid]['counter'][-1] + 1  )
            else:
                self.grant_history[ONU.oid]['counter'].append( 1 )

            #PREDICTIONS
            prediction = self.predictor(ONU.oid) # start predictor process


            #grant_time_file.write( "{},{},{}\n".format(ONU.oid,self.env.now,grant_final_time) )
            # construct grant message
            grant = {'ONU':ONU,'grant_size': buffer_size, 'grant_final_time': grant_final_time, 'prediction': prediction}

            self.grant_store.put(grant) # send grant to OLT

            # timeout until the end of grant to then get next grant request
            yield self.env.timeout(grant_time+delay+ self.guard_interval)

class OLT(object):
    """Optical line terminal"""
    def __init__(self,env,odn,max_grant_size,dba,window,predict):
        self.env = env
        self.grant_store = simpy.Store(self.env) # grant communication between processes
        #choosing algorithms
        if dba == "pd_dba":
            self.dba = PD_DBA(self.env, max_grant_size, self.grant_store,window,predict)
        else:
            self.dba = IPACT(self.env, max_grant_size, self.grant_store)

        self.receiver = self.env.process(self.OLT_receiver(odn)) # process for receiving requests
        self.sender = self.env.process(self.OLT_sender(odn)) # process for sending grant

    def OLT_sender(self,odn):
        """A process which sends a grant message to ONU"""
        while True:
            grant = yield self.grant_store.get() # receive grant from dba
            odn.put_grant(grant['ONU'],grant) # send grant to odn

    def OLT_receiver(self,odn):
        """A process which receives a request message from the ONUs."""
        while True:
            request = yield odn.get_request() #get a request message
            #print("Received Request from ONU {} at {}".format(request['ONU'].oid, self.env.now))
            # send request to DBA
            self.env.process(self.dba.dba(request['ONU'],request['buffer_size']))


#starts the simulator
random.seed(RANDOM_SEED)
env = simpy.Environment()
odn = ODN(env)
ONU_List = []

for i in range(NUMBER_OF_ONUs):
    MAC_TABLE[i] = "00:00:00:00:{}:{}".format(random.randint(0x00, 0xff),random.randint(0x00, 0xff))
    Grant_ONU_counter[i] = 0
MAC_TABLE['olt'] = "ff:ff:ff:ff:00:01"
for i in range(NUMBER_OF_ONUs):
    distance= DISTANCE
    ONU_List.append(ONU(distance,i,env,odn,EXPONENT,ONU_QUEUE_LIMIT,PKT_SIZE,MAX_BUCKET_SIZE))

olt = OLT(env,odn,MAX_GRANT_SIZE,DBA_ALGORITHM,WINDOW,PREDICT)
logging.info("starting simulator")
env.run(until=SIM_DURATION)
delay_file.close()
grant_time_file.close()
pkt_file.close()
mse_file.close
