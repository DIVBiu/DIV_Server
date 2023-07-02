
# without threads

import random
import string
import zlib
import cv2
from util import get_parking_spots_bboxes, empty_or_not
import numpy as np
from flask import Flask
from flask_mongoengine import MongoEngine

app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {
    'db': 'DB',
    'host': 'mongodb+srv://dviramram:Q1w2e3r4@db.sswgsxf.mongodb.net/',
}
db = MongoEngine(app)

class Building(db.Document):
    address = db.StringField(required=True, unique=True)
    tenants = db.ListField(db.ReferenceField('User'))
    chat = db.ListField(db.ReferenceField('Message'))
    surveys = db.ListField(db.ReferenceField('Survey'))
    cars = db.ListField(db.ReferenceField('Car'))
    admin = db.ReferenceField('User', required=True)
    pending_approval_tenants = db.ListField(db.ReferenceField('User'))
    pending_approval_cars = db.ListField(db.ReferenceField('Car'))
    index = db.IntField(required=True, unique=True)
    parking_amount = db.IntField()
    available_parking_amount = db.IntField()
    update_parking_image = db.StringField()

mask = './mask_1920_1080.png'
video_path = './parking_1920_1080_loop.mp4'

mask = cv2.imread(mask, 0)

cap = cv2.VideoCapture(video_path)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
connected_components = cv2.connectedComponentsWithStats(mask, 4, cv2.CV_32S)
spots = get_parking_spots_bboxes(connected_components)

def generate_random_filename(length=10):
    chars = string.ascii_letters + string.digits
    filename = ''.join(random.choice(chars) for _ in range(length))
    return filename


def check_availability(i):
    random_frame_index = random.randint(0, total_frames - 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame_index)

    spots_status = [None for _ in spots]

    building = Building.objects.get(index=i)

    ret, frame = cap.read()

    for spot_index, spot in enumerate(spots):
        x1, y1, w, h = spot

        spot_crop = frame[y1:y1 + h, x1:x1 + w, :]

        spot_status = empty_or_not(spot_crop)
        spots_status[spot_index] = spot_status


        if spot_status:
            frame = cv2.rectangle(frame, (x1, y1), (x1 + w, y1 + h), (0, 255, 0), 2)
        else:
            frame = cv2.rectangle(frame, (x1, y1), (x1 + w, y1 + h), (0, 0, 255), 2)

    cv2.rectangle(frame, (80, 20), (550, 80), (0, 0, 0), -1)
    cv2.putText(frame, 'Available spots: {} / {}'.format(str(sum(spots_status)), str(len(spots_status))), (100, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    building.available_parking_amount = sum(spots_status)

    # Generate a random filename
    filename = generate_random_filename()

    # Load the image using OpenCV

    # Save the image with the generated filename
    cv2.imwrite(filename + '.jpg', frame)

    # compressed_image = zlib.compress(frame, level=9)
    # image_bytes = np.asarray(bytearray(compressed_image), dtype=np.uint8)

    building.update_parking_image = filename + '.jpg'
    building.save()

# until here without threads
# from here with threads

import cv2
import matplotlib.pyplot as plt
import numpy as np
import zlib
from util import get_parking_spots_bboxes, empty_or_not
from flask import Flask
from flask_mongoengine import MongoEngine


# app = Flask(__name__)
# app.config['MONGODB_SETTINGS'] = {
#     'db': 'DB',
#     'host': 'mongodb+srv://dviramram:Q1w2e3r4@db.sswgsxf.mongodb.net/',
# }
# db = MongoEngine(app)
#
# class Building(db.Document):
#     address = db.StringField(required=True, unique=True)
#     tenants = db.ListField(db.ReferenceField('User'))
#     chat = db.ListField(db.ReferenceField('Message'))
#     surveys = db.ListField(db.ReferenceField('Survey'))
#     cars = db.ListField(db.ReferenceField('Car'))
#     admin = db.ReferenceField('User', required=True)
#     pending_approval_tenants = db.ListField(db.ReferenceField('User'))
#     pending_approval_cars = db.ListField(db.ReferenceField('Car'))
#     index = db.IntField(required=True, unique=True)
#     parking_amount = db.IntField()
#     available_parking_amount = db.IntField()
#     update_parking_image = db.BinaryField()


# def calc_diff(im1, im2):
#     return np.abs(np.mean(im1) - np.mean(im2))


# def check_availability(i):
#     building = Building.objects.get(index=i)
#
#     mask = './mask_1920_1080.png'
#     video_path = './parking_1920_1080_loop.mp4'
#
#     mask = cv2.imread(mask, 0)
#
#     cap = cv2.VideoCapture(video_path)
#
#     connected_components = cv2.connectedComponentsWithStats(mask, 4, cv2.CV_32S)
#
#     spots = get_parking_spots_bboxes(connected_components)
#
#     spots_status = [None for _ in spots]
#     # diffs = [None for _ in spots]
#
#     previous_frame = None
#
#     frame_nmr = 0
#     # sample_count = 0
#     interval = 50
#     # ret = True
#     # step = 60000
#     # interval = 10
#
#     while cap.isOpened():
#         frame_nmr = frame_nmr + 1
#         ret, frame = cap.read()
#
#         if not ret:
#             break
#
#
#         if frame_nmr % (interval * int(cap.get(cv2.CAP_PROP_FPS))) == 0:
#             print(f'iteration: {frame_nmr}')
#             # sample_count += 1
#             for spot_indx, spot in enumerate(spots):
#                 x1, y1, w, h = spot
#
#                 spot_crop = frame[y1:y1 + h, x1:x1 + w, :]
#
#                 spot_status = empty_or_not(spot_crop)
#
#                 spots_status[spot_indx] = spot_status
#
#                 if spot_status:
#                     frame = cv2.rectangle(frame, (x1, y1), (x1 + w, y1 + h), (0, 255, 0), 2)
#                 else:
#                     frame = cv2.rectangle(frame, (x1, y1), (x1 + w, y1 + h), (0, 0, 255), 2)
#
#             cv2.rectangle(frame, (80, 20), (550, 80), (0, 0, 0), -1)
#             cv2.putText(frame, 'Available spots: {} / {}'.format(str(sum(spots_status)), str(len(spots_status))),
#                         (100, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
#
#             building.available_parking_amount = sum(spots_status)
#
#             # compressed_image = zlib.compress(frame, level=9)
#             # image_bytes = np.asarray(bytearray(compressed_image), dtype=np.uint8)
#             #
#             # building.update_parking_image = image_bytes.tobytes()
#             building.save()
#
#             print(f'thread {i}, num of free slots: {sum(spots_status)}')
            # cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
            # cv2.imshow('frame', frame)


            # for spot_indx, spot in enumerate(spots):
            #     spot_status = spots_status[spot_indx]
            #     x1, y1, w, h = spots[spot_indx]
            #
            #     if spot_status:
            #         frame = cv2.rectangle(frame, (x1, y1), (x1 + w, y1 + h), (0, 255, 0), 2)
            #     else:
            #         frame = cv2.rectangle(frame, (x1, y1), (x1 + w, y1 + h), (0, 0, 255), 2)


        # if frame_nmr % step == 0 and previous_frame is not None:
        #     for spot_indx, spot in enumerate(spots):
        #         x1, y1, w, h = spot
        #
        #         spot_crop = frame[y1:y1 + h, x1:x1 + w, :]
        #
        #         diffs[spot_indx] = calc_diff(spot_crop, previous_frame[y1:y1 + h, x1:x1 + w, :])
        #
        #     print([diffs[j] for j in np.argsort(diffs)][::-1])

        # if frame_nmr % step == 0:
        #     if previous_frame is None:
        #         arr_ = range(len(spots))
        #     else:
        #         arr_ = [j for j in np.argsort(diffs) if diffs[j] / np.amax(diffs) > 0.4]
        #     for spot_indx in arr_:
        #         spot = spots[spot_indx]
        #         x1, y1, w, h = spot
        #
        #         spot_crop = frame[y1:y1 + h, x1:x1 + w, :]
        #
        #         spot_status = empty_or_not(spot_crop)
        #
        #         spots_status[spot_indx] = spot_status


        # if frame_nmr % step == 0:
        #     previous_frame = frame.copy()

        # for spot_indx, spot in enumerate(spots):
        #     spot_status = spots_status[spot_indx]
        #     x1, y1, w, h = spots[spot_indx]
        #
        #     if spot_status:
        #         frame = cv2.rectangle(frame, (x1, y1), (x1 + w, y1 + h), (0, 255, 0), 2)
        #     else:
        #         frame = cv2.rectangle(frame, (x1, y1), (x1 + w, y1 + h), (0, 0, 255), 2)
        #
        # cv2.rectangle(frame, (80, 20), (550, 80), (0, 0, 0), -1)
        # cv2.putText(frame, 'Available spots: {} / {}'.format(str(sum(spots_status)), str(len(spots_status))), (100, 60),
        #             cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        #
        # building.available_parking_amount = sum(spots_status)
        #
        # compressed_image = zlib.compress(frame, level=9)
        # image_bytes = np.asarray(bytearray(compressed_image), dtype=np.uint8)
        #
        # building.update_parking_image = image_bytes.tobytes()
        # building.save()
        #
        # print(f'thread {i}, num of free slots: {sum(spots_status)}')
        #
        # # cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
        # # cv2.imshow('frame', frame)
        #
        # if cv2.waitKey(25) & 0xFF == ord('q'):
        #     break
        #
        # frame_nmr += 1

    # cap.release()
    # cv2.destroyAllWindows()

# until here with threads


# if __name__ == '__main__':
#     check_availability(1)
