#!/usr/bin/env python

import cv2
import numpy as np
import rospy
import math
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import CompressedImage, Image


class CropRowFind(object):
    def __init__(self):
        self.vision = VisionCV2()
        self.rows = None

    def find_rows(self, data):
        self.rows = self.vision.find_rows(data)
        return self.rows

    def draw_rows(self, img):
        if self.rows is not None:
            for x in range(0, len(self.rows)):
                for x1, y1, x2, y2 in self.rows[x]:
                    cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 10)
        return img


class VisionCV2(CropRowFind):
    def __init__(self):
        self.window = (150, 450, 580, 880)
        self.sigma = 10
        self.gauss_kernel = (5, 5)
        self.close_open_kernels = ((20, 20), (10, 10))
        self.hough_params = (1, 180, 250, 100, 50)

    def find_rows(self, data):
        # img = self.roi(data)
        img = self.blur(data)
        img = self.egvi(img)
        img = self.close_open(img)
        rt, img = self.threshold(img)
        return self.lines(img)

    def roi(self, img):
        return img[self.window[0]:self.window[1], self.window[2]:self.window[3]]

    def blur(self, img):
        return cv2.GaussianBlur(img, self.gauss_kernel, self.sigma)

    def egvi(self, img):
        b, g, r = cv2.split(img)
        return 2 * g - r - b

    def close_open(self, img):
        closed = cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones(self.close_open_kernels[0], np.uint8))
        return cv2.morphologyEx(closed, cv2.MORPH_OPEN, np.ones(self.close_open_kernels[1], np.uint8))

    def threshold(self, img):
        return cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    def lines(self, img):
        return cv2.HoughLinesP(image=img, rho=self.hough_params[0], theta=np.pi / self.hough_params[1],
                               threshold=self.hough_params[2], minLineLength=self.hough_params[3],
                               maxLineGap=self.hough_params[4])


class CropRowFollow(object):
    def __init__(self):
        self.rows_img_pub = rospy.Publisher('rows_img', Image, queue_size=1)
        self.img_sub = rospy.Subscriber('camera/image_color/compressed', CompressedImage, self.crop_image_cb)
        self.bridge = CvBridge()
        self.crf = CropRowFind()

    def crop_image_cb(self, data):
        try:
            img = self.bridge.compressed_imgmsg_to_cv2(data)
            self.crf.find_rows(img)
            rows_img = self.crf.draw_rows(img)
            if rows_img is not None:
                self.rows_img_pub.publish(self.bridge.cv2_to_imgmsg(rows_img, 'bgr8'))
            else:
                rospy.loginfo('No Image')
        except CvBridgeError as e:
            print e


def main():
    rospy.init_node('crop_row_follow', anonymous=True)
    CropRowFollow()
    while not rospy.is_shutdown():
        rospy.spin()


if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
