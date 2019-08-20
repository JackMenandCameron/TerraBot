/*
 * Automated Systems Arduino File
 */

#include <ros.h>
#include <std_msgs/Int32.h>
#include <std_msgs/Float32.h>
#include <std_msgs/Empty.h>
#include <std_msgs/Bool.h>
#include <std_msgs/Float32MultiArray.h>
#include <std_msgs/Int32MultiArray.h>
#include <SimpleDHT.h>

byte temperature;
byte humidity;
int lvl = 0;

ros::NodeHandle  nh;
int DHT_pin = 52;
SimpleDHT22 dht(DHT_pin);

int light_pin = A0;

int trig_pin = 48;
int echo_pin = 50;

int smoist_pin = A1;
int cur_pin = A2;


int led_pin = 9;
int wpump_pin = 12;
int fan_pin = 8;

float last_update = 0;
float last_dht = 0;
float time_now = 0;
int interval = 1000;

//Was long but unsure why
int light_sum = 0;
int light_count = 0;

int cur_sum = 0;
int cur_count = 0;


//Frequency Adjustment
void freq_change( const std_msgs::Float32& cmd_msg){
  interval = round(1000.0 / cmd_msg.data);
}

ros::Subscriber<std_msgs::Float32> freq_sub("freq_raw", &freq_change);

// Functions for Actuators
void led_activate( const std_msgs::Int32& cmd_msg){
  analogWrite(led_pin, cmd_msg.data);//toggle led
}

void wpump_activate(const std_msgs::Bool cmd_msg){
  analogWrite(wpump_pin, cmd_msg.data ? 75 : 0);
}

void fan_activate(const std_msgs::Bool& cmd_msg){
  analogWrite(fan_pin, cmd_msg.data ? 255 : 0);
}

// Actuators
ros::Subscriber<std_msgs::Int32> led_sub("led_raw", &led_activate);
ros::Subscriber<std_msgs::Bool> wpump_sub("wpump_raw", &wpump_activate);
ros::Subscriber<std_msgs::Bool> fan_sub("fan_raw", &fan_activate);


// Sensor helpers
float get_level() {
  float duration;
  digitalWrite(trig_pin, LOW);
  delayMicroseconds(2);
  digitalWrite(trig_pin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig_pin, LOW);
  duration = float(pulseIn(echo_pin, HIGH, 10000));
  return duration / 5.82;
}

// Sensors

std_msgs::Int32MultiArray humid_msg;
ros::Publisher humid_pub("humid_raw", &humid_msg);

std_msgs::Int32MultiArray temp_msg;
ros::Publisher temp_pub("temp_raw", &temp_msg);

std_msgs::Int32MultiArray light_msg;
ros::Publisher light_pub("light_raw", &light_msg);

std_msgs::Float32 level_msg;
ros::Publisher level_pub("level_raw", &level_msg);

std_msgs::Float32MultiArray cur_msg;
ros::Publisher cur_pub("cur_raw", &cur_msg);

std_msgs::Int32MultiArray smoist_msg;
ros::Publisher smoist_pub("smoist_raw", &smoist_msg);

void setup(){
  pinMode(led_pin, OUTPUT);
  pinMode(wpump_pin, OUTPUT);
  pinMode(fan_pin, OUTPUT);
  pinMode(trig_pin, OUTPUT);
  pinMode(echo_pin, INPUT);

  nh.initNode();
  nh.subscribe(freq_sub);

  nh.subscribe(led_sub);
  nh.subscribe(wpump_sub);
  nh.subscribe(fan_sub);

  nh.advertise(temp_pub);
  nh.advertise(humid_pub);
  nh.advertise(light_pub);
  nh.advertise(level_pub);
  nh.advertise(smoist_pub);
  nh.advertise(cur_pub);
}

float to_amp(int analog) {
  return (float(analog) - 512) * .0491;
}
void loop(){
  if (light_count < 1000) {
    light_count++;
    light_sum += analogRead(light_pin);
  }

  if (cur_count < 1000) {
    cur_count++;
    cur_sum += analogRead(cur_pin);
  }

  if(millis() - last_dht > 2500){
      dht.read(&temperature, &humidity, NULL);
      last_dht = millis();
  }

  if(millis() - last_update > interval){
      last_update = millis();
      temp_msg.data_length = 2;
      long int t_array[2];
      if (temperature)
	long int t_array[2] = {temperature, temperature};
      else
	long int t_array[2] = {0,0};
      temp_msg.data = t_array;
      temp_pub.publish(&temp_msg);

      humid_msg.data_length = 2;
      long int h_array[2];
      if (humidity)
	long int h_array[2] = {humidity, humidity};
      else
	long int h_array[2] = {0,0};
      humid_msg.data = h_array;
      humid_pub.publish(&humid_msg);

      light_msg.data_length = 2;
      long int l_array[2] = { light_sum / light_count, light_sum / light_count };
      light_msg.data = l_array;
      light_sum = 0;
      light_count = 0;
      light_pub.publish(&light_msg);

      level_msg.data = get_level();
      level_pub.publish(&level_msg);

      smoist_msg.data_length = 2;
      long int s_array[2] = {analogRead(smoist_pin), analogRead(smoist_pin)};
      smoist_msg.data = s_array;
      smoist_pub.publish(&smoist_msg);

      cur_msg.data_length = 2;
      float c_array[2] = { to_amp(cur_sum / cur_count), to_amp(cur_sum / cur_count) };
      cur_msg.data = c_array;
      cur_sum = 0;
      cur_count = 0;
      cur_pub.publish(&cur_msg);
  }
  nh.spinOnce();
}