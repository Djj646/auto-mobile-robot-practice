#!/usr/bin/env python3
import sys
import matplotlib.pyplot as plt
import numpy as np
import rospy
import tf
from course_agv_nav.srv import Plan, PlanResponse
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid, Path
from nav_msgs.srv import GetMap

## TODO import your own planner
from astar import PRM as Planner
#from rrt import RRT as Planner

class GlobalPlanner:
    def __init__(self):
        # 起点
        self.plan_sx = 0.0
        self.plan_sy = 0.0
        # 终点
        self.plan_gx = 8.0
        self.plan_gy = -8.0
        # 采样参数与机器人半径
        self.plan_grid_size = 0.3
        self.plan_robot_radius = 0.6
        # 障碍物列表
        self.plan_ox = []
        self.plan_oy = []
        # 规划路径
        self.plan_rx = []
        self.plan_ry = []

        # count to update map
        self.map_count = 0

        self.tf = tf.TransformListener()
        self.goal_sub = rospy.Subscriber('/course_agv/goal',PoseStamped,self.goalCallback)
        # 提供 重新规划 服务
        self.plan_srv = rospy.Service('/course_agv/global_plan',Plan,self.replan)
        # 规划路径发布
        self.path_pub = rospy.Publisher('/course_agv/global_path',Path,queue_size = 1)
        # 订阅地图更新
        self.map_sub = rospy.Subscriber('/slam_map',OccupancyGrid,self.mapCallback)
        self.updateMap()
        # self.updateGlobalPose()

    def goalCallback(self,msg):
        self.plan_goal = msg
        self.plan_gx = msg.pose.position.x
        self.plan_gy = msg.pose.position.y
        print("get new goal!!! ",self.plan_goal)
        self.replan()

    def collisionCallback(self,msg):
        self.replan()

    def updateGlobalPose(self):
        try:
            self.tf.waitForTransform("/map", "/robot_base", rospy.Time(), rospy.Duration(4.0))
            (self.trans,self.rot) = self.tf.lookupTransform('/map','/robot_base',rospy.Time(0))
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            print("get tf error!")
        # 机器人位置 即起点
        self.plan_sx = self.trans[0]
        self.plan_sy = self.trans[1]

    def replan(self):
        print('get request for replan!!!!!!!!')
        self.initPlanner()
        self.updateGlobalPose()
        ## TODO get planner result
        self.plan_rx,self.plan_ry = self.planner.plan(self.plan_sx,self.plan_sy,self.plan_gx,self.plan_gy,self.plan_ox,self.plan_oy)
        print("get map")
        self.publishPath()
        res = True
        return PlanResponse(res)
        
    def initPlanner(self):
        map_data = np.array(self.map.data).reshape((self.map.info.height, -1)).transpose()
        ox,oy = np.nonzero(map_data > 50)
        self.plan_ox = (ox*self.map.info.resolution+self.map.info.origin.position.x).tolist()
        self.plan_oy = (oy*self.map.info.resolution+self.map.info.origin.position.y).tolist()
        #print(self.plan_ox,self.plan_oy)
        ## TODO init your planner
        self.planner = Planner()

    def mapCallback(self,msg):
        self.map = msg

    def updateMap(self):
        rospy.wait_for_service('/static_map')
        try:
            # 请求 GetMap 服务代理
            getMap = rospy.ServiceProxy('/static_map',GetMap)
            msg = getMap().map
        except:
            e = sys.exc_info()[0]
            print('Service call failed: %s'%e)
        # Update for planning algorithm       
        self.mapCallback(msg)


    def publishPath(self):
        '''
        规划好的路径(x,y)转为pose列表path, 发布, 用于绘制
        '''
        path = Path()
        path.header.seq = 0
        path.header.stamp = rospy.Time(0)
        path.header.frame_id = 'map'
        for i in range(len(self.plan_rx)):
            pose = PoseStamped()
            pose.header.seq = i
            pose.header.stamp = rospy.Time(0)
            pose.header.frame_id = 'map'
            pose.pose.position.x = self.plan_rx[len(self.plan_rx)-1-i]
            pose.pose.position.y = self.plan_ry[len(self.plan_rx)-1-i]
            pose.pose.position.z = 0.01
            pose.pose.orientation.x = 0
            pose.pose.orientation.y = 0
            pose.pose.orientation.z = 0
            pose.pose.orientation.w = 1
            path.poses.append(pose)
        
        # 发布
        self.path_pub.publish(path)


def main():
    rospy.init_node('global_planner')
    gp = GlobalPlanner()
    gp.initPlanner()
    gp.replan()
    rospy.spin()
    pass

if __name__ == '__main__':
    main()
