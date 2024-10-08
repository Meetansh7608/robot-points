import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud
from geometry_msgs.msg import Twist, Pose2D
import math, time

class ReachTargets(Node):
    def __init__(self):
        super().__init__('reach_targets')
        self.unvisited_targets = []
        self.current_pose = None
        
        self.pose_sub = self.create_subscription(Pose2D, '/pose', self.pose_callback, 10)
        self.target_sub = self.create_subscription(PointCloud, '/unvisited_targets', self.targets_callback, 10)
        
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.state = 'idle'
        self.target = None
        self.distance = 0
        self.dist_left = None
        
        self.timer = self.create_timer(1, self.timer_callback)
        
    def pose_callback(self, msg):
        self.current_pose = msg
        
    def targets_callback(self, msg):
        self.unvisited_targets = msg.points
        if not msg.points:
            # self.get_logger().info('All targets visited.')
            rclpy.shutdown()
            exit()
        
    def find_closest(self):
        if not self.unvisited_targets or not self.current_pose:
            return None, None
        
        closest = None
        dist = float('inf')
        
        for targets in self.unvisited_targets:
            d = ((self.current_pose.x - targets.x) ** 2 + (self.current_pose.y - targets.y) ** 2) ** 0.5
            if d < dist:
                dist = d
                closest = targets
        return closest, dist
    
    def stop(self):
        msg = Twist()
        self.publisher_.publish(msg)
    
    def rotate(self, angle):
        msg = Twist()
        msg.angular.z = 1.0 if angle > 0 else -1.0
        
        if abs(angle) > 1.0:
            self.publisher_.publish(msg)
        else:
            msg.angular.z = angle
            self.publisher_.publish(msg)
        
    def move(self, distance):
        msg = Twist()
        msg.linear.x = 1.0
        
        if distance > 1.0:
            self.dist_left -= 1.0
            self.publisher_.publish(msg)
        else:
            msg.linear.x = distance
            self.dist_left -= distance
            self.publisher_.publish(msg)
        
    def timer_callback(self):
        if self.current_pose is None:
            # self.get_logger().info('No pose data available yet.')
            return
        
        # self.get_logger().info(f'Current state: {self.state}')
        
        if self.state == 'idle':
            self.target, self.distance = self.find_closest()
            if self.target is None:
                # self.get_logger().info('No targets available.')
                return
            
            self.state = 'rotate'
        
        elif self.state == 'rotate':
            angle = math.atan2((self.target.y - self.current_pose.y), (self.target.x - self.current_pose.x)) 
            
            # self.get_logger().info(f'\t\t Angle: {angle}')
            # self.get_logger().info(f'\t\t Current theta: {self.current_pose.theta}')
            # self.get_logger().info(f'\t\t Angle diff: {angle - self.current_pose.theta}')
            
            route1 = angle - self.current_pose.theta
            route2 = route1 + math.pi * 2 if route1 < 0 else route1 - math.pi * 2
            
            if abs(route1) < abs(route2):
                angle = route1
            else:
                angle = route2
            
            if abs(angle) < 1e-4:
                self.stop()
                self.state = 'move'
                self.dist_left = self.distance
            else:
                # self.get_logger().info(f'Rotating by {angle}')
                self.rotate(angle)
        
        elif self.state == 'move':
            self.distance = ((self.current_pose.x - self.target.x) ** 2 + (self.current_pose.y - self.target.y) ** 2) ** 0.5
            if self.distance < 0.01 or self.dist_left < 0.01:
                self.stop()
                self.state = 'idle'
                self.target = None
                self.distance = 0
                self.dist_left = None
            else:
                # self.get_logger().info(f'Moving by {self.distance}')
                self.move(self.distance)
                # self.state = 'rotate'
        
def main(args=None):
    rclpy.init(args=args)
    reach_targets = ReachTargets()
    rclpy.spin(reach_targets)
    reach_targets.destroy_node()
    rclpy.shutdown()
    
if __name__ == '__main__':
    main()