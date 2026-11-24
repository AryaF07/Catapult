"""The original hackathon targeting logic, kept verbatim (minus hardware
calls) so the simulator can compare it against the optimised version."""


def filter_reading(angle, distances):
    distances = sorted(distances)
    median_distance = distances[len(distances) // 2]
    if 25 < median_distance < 1400:
        return (angle, median_distance)
    return None


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
            if abs(current_angle - previous_angle) <= 100:
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
