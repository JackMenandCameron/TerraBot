#!/usr/bin/env python

#mock file of student
import rospy
from std_msgs.msg import Int32
from std_msgs.msg import Float32
from std_msgs.msg import Bool

light = 0
led_level = 0
w_level = 3

rospy.init_node("student", anonymous = True)

wpump_pub = rospy.Publisher("wpump_input", Bool, queue_size = 100)
npump_pub = rospy.Publisher("npump_input", Bool, queue_size = 100)
apump_pub = rospy.Publisher("apump_input", Bool, queue_size = 100)
led_pub = rospy.Publisher("led_input", Int32, queue_size = 100)

freq_pub = rospy.Publisher("freq_input", Float32, queue_size = 100)

def humid_reaction(data):
    True

def temp_reaction(data):
    True

def light_reaction(data):
    global light
    light = data.data

def level_reaction(data):
    global w_level
    w_level = data.data

def tds_reaction(data):
    True

humid_sensor = rospy.Subscriber("humid_output", Int32, humid_reaction)
temp_sensor = rospy.Subscriber("temp_output", Int32, temp_reaction)
light_sensor = rospy.Subscriber("light_output", Int32, light_reaction)
level_sensor = rospy.Subscriber("level_output", Int32, level_reaction)
tds_sensor = rospy.Subscriber("tds_output", Int32, tds_reaction)

freq_pub.publish(1)

while not rospy.core.is_shutdown():
    if light - 90 < 0:
        led_level = min(255, led_level + 1)
    else:
        led_level = max(0, led_level - 1)
    led_pub.publish(led_level)
#    print([light,led_level])
    wpump_pub.publish(True if w_level == 0 else False)
    rospy.rostime.wallsleep(0.01)

