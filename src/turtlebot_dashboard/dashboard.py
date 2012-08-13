import roslib;roslib.load_manifest('turtlebot_dashboard')
import rospy

import diagnostic_msgs
import turtlebot_node.srv
import turtlebot_node.msg

from robot_dashboard.dashboard import Dashboard
from robot_dashboard.widgets import MonitorDashWidget, ConsoleDashWidget, MenuDashWidget, ButtonDashWidget, BatteryDashWidget
from QtGui import QMessageBox, QAction

from .battery import TurtlebotBattery

class TurtlebotDashboard(Dashboard):
    def setup(self, context):
        self.message = None

        self._dashboard_message = None
        self._last_dashboard_message_time = 0.0

        self._raw_byte = None
        self.digital_outs = [0,0,0]
        
        self._dashboard_agg_sub = rospy.Subscriber('diagnostics_agg', diagnostic_msgs.msg.DiagnosticArray, self.dashboard_callback)
        self._power_control = rospy.ServiceProxy('turtlebot_node/set_digital_outputs', turtlebot_node.srv.SetDigitalOutputs)

    def get_widgets(self):
        self.mode = MenuDashWidget(self.context, 'Mode', icon = 'cog.svg')

        self.mode.add_action('Full', self.on_full_mode)
        self.mode.add_action('Passive', self.on_passive_mode)
        self.mode.add_action('Safe', self.on_safe_mode)

        self.states = ["QPushButton {background-color: red}",
                       "QPushButton {background-color: green}"]
        
        self.breakers = [ButtonDashWidget(self.context, 'breaker0', lambda: self.toggle_breaker(0) , 'bolt.svg', self.states), 
                         ButtonDashWidget(self.context, 'breaker1', lambda: self.toggle_breaker(1) , 'bolt.svg', self.states),
                         ButtonDashWidget(self.context, 'breaker2', lambda: self.toggle_breaker(2) , 'bolt.svg', self.states)]

        self.create_bat = TurtlebotBattery(self.context)
        self.lap_bat = TurtlebotBattery(self.context)
        self.batteries = [self.create_bat, self.lap_bat]

        return [[MonitorDashWidget(self.context), ConsoleDashWidget(self.context), self.mode],
                self.breakers,
                self.batteries]

    def dashboard_callback(self, msg):
        self._dashboard_message = msg
        self._last_dashboard_message_time = rospy.get_time()
  
        battery_status = {}
        laptop_battery_status = {}
        breaker_status = {}
        op_mode = None
        for status in msg.status:
            if status.name == "/Power System/Battery":
                for value in status.values:
                    battery_status[value.key]=value.value
            if status.name == "/Power System/Laptop Battery":
                for value in status.values:
                    laptop_battery_status[value.key]=value.value
            if status.name == "/Mode/Operating Mode":
                op_mode=status.message
            if status.name == "/Digital IO/Digital Outputs":
                #print "got digital IO"
                for value in status.values:
                    breaker_status[value.key]=value.value
  
        if (battery_status):
          self.create_bat.set_power_state(battery_status)
        else:
          #self._power_state_ctrl.set_stale()
          print("Power State Stale")
  
        #if (laptop_battery_status):
        #  self._power_state_ctrl_laptop.set_power_state(laptop_battery_status)
        #else:
        #  self._power_state_ctrl_laptop.set_stale()
        
        if (breaker_status):
            self._raw_byte = int(breaker_status['Raw Byte'])
            self._update_breakers()

    def toggle_breaker(self, index):
        try:
            self.digital_outs[index] = not self.digital_outs[index]
            power_cmd = turtlebot_node.srv.SetDigitalOutputsRequest(self.digital_outs[0], self.digital_outs[1], self.digital_outs[2])
            #print power_cmd
            self._power_control(power_cmd)

            return True
        except rospy.ServiceException, e:
            self.message = QMessageBox()
            self.message.setText("Service call failed with error: %s"%(e))
            self.message.exec_()
            return False
          
        return False

    def _update_breakers(self):
        tmp = self._raw_byte
        for i in range(0,3):
            self.digital_outs[i]=tmp%2
            self.breakers[i].update_state(self.digital_outs[i])
            tmp = tmp >> 1
        
    def on_passive_mode(self):
        passive = rospy.ServiceProxy("/turtlebot_node/set_operation_mode",turtlebot_node.srv.SetTurtlebotMode )
        try:
            passive(turtlebot_node.msg.TurtlebotSensorState.OI_MODE_PASSIVE)
        except rospy.ServiceException, e:
            self.message = QMessageBox()
            self.message.setText("Failed to put the turtlebot in passive mode: service call failed with error: %s"%(e))
            self.message.exec_() 

    def on_safe_mode(self):
        safe = rospy.ServiceProxy("/turtlebot_node/set_operation_mode",turtlebot_node.srv.SetTurtlebotMode)
        try:
          safe(turtlebot_node.msg.TurtlebotSensorState.OI_MODE_SAFE)
        except rospy.ServiceException, e:
          self.message = QMessageBox()
          self.message.setText("Failed to put the turtlebot in safe mode: service call failed with error: %s"%(e))
          self.message.exec_()

    def on_full_mode(self):
        full = rospy.ServiceProxy("/turtlebot_node/set_operation_mode", turtlebot_node.srv.SetTurtlebotMode)
        try:
            full(turtlebot_node.msg.TurtlebotSensorState.OI_MODE_FULL)
        except rospy.ServiceException, e:
            self.message = QMessageBox()
            self.message.setText("Failed to put the turtlebot in full mode: service call failed with error: %s"%(e))
            self.message.exec_()
