#!/usr/bin/env python
import rospy
from std_msgs.msg import Int32,Bool,Float32,String,Int32MultiArray,Float32MultiArray
from topic_def import *
from rosgraph_msgs.msg import Clock
import time
import argparse

parser = argparse.ArgumentParser(description = "simulator parser for Autonomous Systems")
parser.add_argument('--baseline', type = str, default = "baseline.txt", nargs = "?")
parser.add_argument('--speedup', type = float, default = 1, nargs = "?")
parser.add_argument('-l', '--log', action = 'store_true')
args = parser.parse_args()
is_logging = args.log
#print("Baseline: " + args.baseline)
#print("Speedup: " + str(args.speedup))

try:
    exec(open(args.baseline).read())
except:
    print('no baseline file found')
    exit()

actuator_vars = init_actuators
internal_vars = init_internals
publishers = {}
subscribers = {}
clock_pub = None

###CONSTANTS
evap_rate = 10/3600.0 # moisture sensor decrease 10 units/hour
soak_rate = 20 # moisture sensor increases 20 units/second
flow_rate = 30.0 #ml/sec
humidity_rate = 20/3600.0 # humidity sensor increases 20 units/hour
dehumidity_rate = 20/60.0 # fan decreases humidity by 20 units/minute
warming_rate = 1/60.0 # temperature increases 1 degree Celcius/minute with lights on
cooling_rate = 10/60.0 # fan decreases temperature by 10 units/minute
led_current = 3.2/255
pump_current = .2
fan_current = .06

max_speedup_pump = 1
max_speedup_fans = 5

def generate_publishers():
    global publishers, clock_pub
    clock_pub = rospy.Publisher("clock", Clock, latch = True, queue_size = 1)
    for name in sensor_names:
        pub_name = name + "_raw"
        publishers[name] = rospy.Publisher(
                            pub_name, sensor_types[name],
                            latch = True, queue_size = 100)

#used when generating subs
def update_keyval(dictionary, name, data):
    dictionary[name] = data.data

def generate_cb(dictionary, name):
    return (lambda data: update_keyval(dictionary,name,data))

def generate_subscribers():
    global subscribers
    rospy.Subscriber('speedup', Int32, speedup_cb)    
    for name in actuator_names:
        sub_name = name + "_raw"
        subscribers[name] = rospy.Subscriber(sub_name,
                                actuator_types[name],
                                generate_cb(actuator_vars, name))

default_speedup = args.speedup
speedup = default_speedup

### Change the speedup interactively
def speedup_cb(data):
    global default_speedup
    speedup = data.data
    if (default_speedup != speedup):
        print("speedup_pub %d" %speedup)
        default_speedup = speedup

def amb_light(time):
    return 100

### INTERNAL UPDATE FUNCTIONS ###
def light_update(cur_interval):
    for i in range(2):
        val = internal_vars['light'][i]
        val = actuator_vars['led'] * 3 + amb_light(rospy.get_time())
        internal_vars['light'][i] = min(255, max(0, val))

def volume_update(cur_interval):
    if actuator_vars['wpump']:
        internal_vars['volume'] -= cur_interval * flow_rate
        internal_vars['volume'] = max(0.01, internal_vars['volume'])

def humidity_update(cur_interval):
    for i in range(2):
        val = internal_vars['humidity'][i]
        if actuator_vars['fan']:
            val -= cur_interval * dehumidity_rate
        # The moister it is, the faster humidity increases
        val += cur_interval * humidity_rate * internal_vars['smoist'][i]/600
        internal_vars['humidity'][i] = min(100, max(0, val))

def temperature_update(cur_interval):
    for i in range(2):
        val = internal_vars['temperature'][i]
        if actuator_vars['fan']:
            val -= cur_interval * cooling_rate
        val += (cur_interval * warming_rate * actuator_vars['led']/255.0)
        internal_vars['temperature'][i] = min(40, max(15, val))

def current_update(cur_interval):
    val = (512 + led_current * actuator_vars['led'] +
           (pump_current if actuator_vars['wpump'] else 0) +
           (fan_current if actuator_vars['fan'] else 0))
    internal_vars['current'][0] = val
    # energy += power; power = current* voltage
    internal_vars['current'][1] += cur_interval * (val*12)

def smoist_update(cur_interval):
    for i in range(2):
        val = internal_vars['smoist'][i]
        if (actuator_vars['wpump'] and internal_vars['volume'] > 0):
            val += cur_interval * soak_rate
        val -= cur_interval * evap_rate
        internal_vars['smoist'][i] = min(1000, max(0, val))


update_funcs = {
    'volume'   : volume_update,
    'light' : light_update,
    'temperature' : temperature_update,
    'humidity'  : humidity_update,
    'current' : current_update,
    'smoist'      : smoist_update
}

### INTERNAL TO SENSOR TRANSLATION ###

def get_cur():
    c_array = Float32MultiArray()
    c_array.data = [float(internal_vars['current'][0]), \
                    float(internal_vars['current'][1])]
    return c_array

def get_light():
    l_array = Int32MultiArray()
    l_array.data = [int(internal_vars['light'][0]), \
                    int(internal_vars['light'][1])] 
    return l_array

def get_level():
    return float(internal_vars['volume'] / 20)

def get_temp():
    t_array = Int32MultiArray()
    t_array.data = [int(internal_vars['temperature'][0]), \
                    int(internal_vars['temperature'][1])]
    return t_array

def get_humid():
    h_array = Int32MultiArray()
    h_array.data = [int(internal_vars['humidity'][0]), \
                    int(internal_vars['humidity'][1])]
    return h_array

def get_smoist():
    s_array = Int32MultiArray()
    s_array.data = [int(internal_vars['smoist'][0]), \
                    int(internal_vars['smoist'][1])]
    return s_array


sensor_funcs = {
    'cur'    : get_cur,
    'light'  : get_light,
    'level'  : get_level,
    'temp'   : get_temp,
    'humid'  : get_humid,
    'smoist' : get_smoist
}

rospy.init_node('Simulator', anonymous=True)

generate_publishers()
generate_subscribers()
now = 0
clock_pub.publish(rospy.Time.from_sec(now))
last_update = now

while not rospy.core.is_shutdown():
    cur_interval = now - last_update
    last_update = now
    for f in update_funcs.values():
        f(cur_interval)

    #update sensors (calculations) + publish
    for sensor in sensor_names:
        publishers[sensor].publish(sensor_funcs[sensor]())
    if is_logging:
        print("==========================")
        print(now)
        print(internal_vars)
        print(actuator_vars)

    tick_interval = 1.0/actuator_vars['freq']
    # Don't use rospy.sleep here, because of speedup != 1
    time.sleep(tick_interval)

    old_speedup = speedup
    speedup = min(default_speedup,
                  (max_speedup_pump if actuator_vars['wpump'] else 100000),
                  (max_speedup_fans if actuator_vars['fan'] else 100000))
    if (old_speedup != speedup):
        print("Speedup %d" %speedup)
    now += (tick_interval * speedup)
    clock_pub.publish(rospy.Time.from_sec(now))
