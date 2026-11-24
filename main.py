from larger_servo import Servo
from mini_servo import MiniServo   
from machine import Pin, I2C
from time import sleep_ms
import vl53l0x


deg_90_servo = MiniServo(pin=6)
large_servo = MiniServo(pin=4) 
big_servo = Servo(pin=1)

# a reading is (a,b) where a is angle and b is distance in mm

i2c = I2C(1, sda=Pin(2), scl=Pin(3), freq=400000)
tof = vl53l0x.VL53L0X(i2c) # tof 



def reset():
    deg_90_servo.move_90(direction="CCW")
    sleep_ms(500)
    large_servo.set_us(large_servo.US_180)

    
    

    
# reset()
    # move base to known starting position
    # move vertical servo to known starting position
    # clear previous scan data
    # clear previous filtered data
    # clear previous clusters
    # clear previous target



def horizontal_scan(): # depends on stepper
    scan_data = []

    # replace this with whatever horizontal angles your scan will use
 
    for angle in range(3000, 1799, -100): # 45 to -45 degrees
        large_servo.set_us(angle)#
        sleep_ms(300)
        distances = []
        for _ in range(20):   # take 20 readings at each angle
            distances.append(tof.ping())
            sleep_ms(20)

        distances.sort()
        median_distance = distances[len(distances) // 2]

        # filtering built in here
        if 25 < median_distance < 1400:
            scan_data.append((angle, median_distance))

    return scan_data
    

def find_clusters(filtered_data):
    clusters = []
    if not filtered_data:
        return clusters
    current_cluster = []
    for reading in filtered_data:
        if not current_cluster:
            current_cluster.append(reading)
        else:
            previous_angle = current_cluster[-1][0]
            current_angle = reading[0]
            if abs(current_angle - previous_angle) <= 100: # example threshold
                current_cluster.append(reading)
            else:
                clusters.append(current_cluster)
                current_cluster = [reading]
        
    if current_cluster:
        clusters.append(current_cluster)
    return clusters




def choose_target(clusters):
    if not clusters:
        return None

    def cluster_reading(cluster):
        angles = [reading[0] for reading in cluster]
        distances = sorted(reading[1] for reading in cluster)

        target_angle = (angles[0] + angles[-1]) / 2
        target_distance = distances[len(distances) // 2]

        return (target_angle, target_distance)

    best_target = cluster_reading(clusters[0])

    for cluster in clusters[1:]:
        current_target = cluster_reading(cluster)

        if current_target[1] < best_target[1]:
            best_target = current_target

    return best_target





def fire():
    sleep_ms(500)
    big_servo.turn_180(direction="CW")
    sleep_ms(500)
    deg_90_servo.move_90(direction="CW")
    sleep_ms(500)
    deg_90_servo.move_90(direction="CW")
    sleep_ms(500)
    big_servo.turn_180(direction="CCW")
    sleep_ms(500)
    reset()


def go_to_angle(target_angle):
   large_servo.set_us(target_angle)
   fire()


while True:
    
    scan_data = horizontal_scan()
    clusters = find_clusters(scan_data)
    if clusters:
        target = choose_target(clusters)
        target_angle = target[0] # type: ignore
        target_distance = target[1] # type: ignore
        go_to_angle(target_angle)



# reset system to known start position

# scan_data = horizontal_scan()
# filtered_data = filter_scan(scan_data)
# clusters = find_clusters(filtered_data)

# if clusters is not empty:
#     target = choose_target(clusters)

#     target_angle = target.angle
#     target_distance = target.distance

#     rotate_base_to(target_angle)

#     vertical_scan_data = vertical_scan()
#     midpoint_angle = find_vertical_midpoint(vertical_scan_data)

#     launch_setting = calculate_launch_setting(target_distance, midpoint_angle)

#     aim_launcher(target_angle, midpoint_angle, launch_setting)
#     fire_catapult()

