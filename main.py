import os
import random
import string
import sys
import subprocess
import time
import zlib
from datetime import datetime

import requests
import json
from flask import Flask, jsonify, request
from flask_mongoengine import MongoEngine
from mongoengine.errors import DoesNotExist, ValidationError
from dateutil.parser import parse
import base64
import io
from PIL import Image
import cv2
from util import get_parking_spots_bboxes, empty_or_not
import numpy as np

# from main import amount_of_free_parking
#
from parking_spot_detection_and_counter import check_availability, generate_random_filename

import threading



from licence_plate_recognition_model import licence_plate_recognition

print("Connecting to DB")
app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {
    'db': 'DB',
    'host': 'mongodb+srv://dviramram:Q1w2e3r4@db.sswgsxf.mongodb.net/',
}
db = MongoEngine(app)
print("Connected")

# threads = []








class User(db.Document):
    name = db.StringField(required=True)
    email = db.EmailField(required=True, unique=True)
    password = db.StringField(required=True)
    # buildings = db.ListField(db.ReferenceField('Building'))

    def to_dict(self):
        return {'id': str(self.id), 'name': self.name, 'email': self.email, 'password': self.password}


class Car(db.Document):
    car_number = db.StringField(required=True, unique=True)
    owner = db.ReferenceField('User')

    def to_dict(self):
        return {'id': str(self.id), 'car_number': self.car_number, 'owner': str(self.owner.id)}


class Result(db.Document):
    user = db.ReferenceField('User', required=True)
    choice = db.IntField(required=True)

    def to_dict(self):
        return {'id': str(self.id)}


class Survey(db.Document):
    title = db.StringField(required=True, unique=True)
    question = db.StringField(required=True)
    list_of_answers = db.ListField(db.StringField(), required=True)
    deadline = db.DateTimeField(required=True)
    results = db.ListField(db.ReferenceField('Result'))

    def to_dict(self):
        return {'id': str(self.id), 'question': self.question, 'list_of_answers': self.list_of_answers, 'deadline': self.deadline}


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

    def to_dict(self):
        return {'id': str(self.id), 'address': self.address, 'admin': self.admin, 'tenants': self.tenants, 'chat': self.chat}


class Message(db.Document):
    sender = db.ReferenceField('User', required=True)
    date = db.DateTimeField(required=True)
    content = db.StringField(required=True)

    def to_dict(self):
        return {'id': str(self.id), 'sender': self.sender, 'date': self.date, 'content': self.content}


class Problem(db.Document):
    type = db.IntField(required=True)
    description = db.StringField(required=True)
    status = db.IntField(required=True)
    tenant = db.ReferenceField('User', required=True)
    image = db.StringField()
    date1 = db.DateTimeField(required=True)
    date2 = db.DateTimeField()
    date3 = db.DateTimeField()
    building = db.ReferenceField('Building', required=True)
    remarks = db.ListField(db.StringField())

    def to_dict(self):
        return {'id': str(self.id), 'description': self.description}




@app.route('/users', methods=['GET'])
def get_all_users():
    try:
        users = User.objects()
        return jsonify([user.to_dict() for user in users]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/users/<string:id>', methods=['GET'])
def get_user(id):
    try:
        user = User.objects.get(id=id)
        return jsonify(user.to_dict()), 200
    except DoesNotExist:
        return jsonify({'error': 'User not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid user ID'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/users/login', methods=['GET'])
def login():
    try:
        data = request.args
        email = data.get('email')
        password = data.get('password')
        user = User.objects.get(email=email, password=password)
        return jsonify(user.to_dict()), 200
    except DoesNotExist:
        return jsonify({'error': 'User not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid email or password'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/users/register', methods=['POST'])
def register():
    try:
        data = request.args
        user = User(name=data['name'], email=data['email'], password=data['password'])
        user.save()
        return jsonify(user.to_dict()), 201
    except KeyError:
        return jsonify({'error': 'Missing required field(s)'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/users/get_buildings_by_user', methods=['GET'])
def get_buildings_by_user():
    try:
        data = request.args
        user = User.objects.get(email=data["email"])
        return jsonify({"buildings": [t.address for t in Building.objects(tenants__in=[user])],
                        "pending approval": [t.address for t in Building.objects(pending_approval_tenants__in=[user])]}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/am_I_admin', methods=['GET'])
def am_I_admin():
    try:
        data = request.args
        user = User.objects.get(email=data["email"])
        building = Building.objects.get(address=data["address"])
        if building.admin == user:
            return jsonify({"answer": "yes"}), 201
        else:
            return jsonify({"answer": "no"}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/get_chat_by_building', methods=['GET'])
def get_chat_by_building():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        email = data["email"]
        chat = building.chat
        res_for_client = []
        for msg in chat:
            res_for_client.append({'sender': msg.sender.name, 'sent': msg.sender.email == email, 'date': msg.date.strftime("%Y-%m-%d"), 'content': msg.content})
        return jsonify(res_for_client), 200
        # return jsonify(chat), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/add_message_to_chat', methods=['POST'])
def add_message_to_chat():
    try:
        data = request.args
        email = data.get('email')
        address = data.get('address')
        user = User.objects.get(email=email)
        building = Building.objects.get(address=address)
        content = data.get('content')
        date_string = data.get('date')
        date_object = parse(date_string)
        message = Message(sender=user, date=date_object, content=content)
        message.save()
        building.chat.append(message)
        building.save()
        return jsonify(building.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/users', methods=['POST'])
def create_user():
    try:
        # user_data = request.form
        user_data = request.get_json()
        user = User(name=user_data['name'], email=user_data['email'], password=user_data['password'])
        user.save()
        return jsonify(user.to_dict()), 201
    except KeyError:
        return jsonify({'error': 'Missing required field(s)'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/users/<string:id>', methods=['PUT'])
def update_user(id):
    try:
        # user_data = request.form
        user_data = request.get_json()
        user = User.objects.get(id=id)
        user.name = user_data.get('name', user.name)
        user.password = user_data.get('password', user.password)
        user.email = user_data.get('email', user.email)
        user.save()
        return jsonify(user.to_dict()), 200
    except DoesNotExist:
        return jsonify({'error': 'User not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid user ID'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/users/<string:id>', methods=['DELETE'])
def delete_user(id):
    try:
        user = User.objects.get(id=id)
        user.delete()
        return '', 204
    except DoesNotExist:
        return jsonify({'error': 'User not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid user ID'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings', methods=['GET'])
def get_all_Buildings():
    try:
        Buildings = Building.objects()
        return jsonify([Building.to_dict() for Building in Buildings]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/users/get_name_by_email', methods=['GET'])
def get_name_by_email():
    try:
        data = request.args
        email = data.get('email')
        user = User.objects.get(email=email)
        return jsonify(user.name), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/buildings/<string:id>', methods=['GET'])
def get_Building(id):
    try:
        building = Building.objects.get(id=id)
        return jsonify(building.to_dict()), 200
    except DoesNotExist:
        return jsonify({'error': 'Building not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid Building ID'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_lowest_available_index():
    buildings = Building.objects.order_by('index').only('index')
    if not buildings:
        return 0
    return buildings[len(buildings)-1].index + 1

@app.route('/buildings/new_building', methods=['PUT'])
def create_Building():
    try:
        data = request.args
        admin = User.objects.get(email=data['email'])
        building = Building(address=data['address'], admin=admin, index=get_lowest_available_index(), parking_amount=396
                            , available_parking_amount=0, update_parking_image="")

        building.tenants.append(admin)
        building.save()

        #if you want threads - run this:
        thread = threading.Thread(target=check_availability, args=(building.index,))
        thread.start()
        # until here if you want threads

        return jsonify(building.to_dict()), 201
    except KeyError:
        return jsonify({'error': 'Missing required field(s)'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/building/new_problem', methods=['POST'])
def new_problem():
    try:
        data = request.form
        building = Building.objects.get(address=data['address'])
        user = User.objects.get(email=data['email'])
        type = data['type']
        description = data['description']
        client_date = parse(data['date'])
        if (data['image'] != ""):
            image_data = base64.b64decode(data['image'].replace(" ", "+"))
            np_arr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            file_name = generate_random_filename() + '.jpg'
            cv2.imwrite(file_name, image)

            problem = Problem(type=type, description=description, status=1, tenant=user, date1=client_date,
                              image=file_name, building=building)
        else:
            problem = Problem(type=type, description=description, status=1, tenant=user, date1=client_date,
                              image="", building=building)
        problem.save()
        return jsonify(problem.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_problems', methods=['GET'])
def get_problem():
    try:
        types = ["", "Electricity", "Plumbing", "infrastructure", "Construction", "Other"]
        statuses = ["", "opened", "in treatment", "solved"]
        data = request.args
        building = Building.objects.get(address=data['address'])
        user = User.objects.get(email=data['email'])
        problems = Problem.objects()
        res_for_client = []
        for problem in problems:
            if problem.tenant == user and problem.building == building and not problem.status == 3:

                path_image = problem.image
                if path_image == "":
                    image_str = ""
                else:
                    img = cv2.imread("./" + path_image)
                    # Define compression parameters
                    compression_params = [cv2.IMWRITE_JPEG_QUALITY, 90]  # Adjust quality as desired (0-100)

                    # Compress the image to JPEG format
                    _, compressed_image = cv2.imencode('.jpg', img, compression_params)

                    # Convert the compressed image to a string in base64 format
                    image_str = base64.b64encode(compressed_image).decode('utf-8')

                res_for_client.append(
                    {'id': str(problem.id), 'type': types[problem.type], 'description': problem.description,
                     'opening_date': problem.date1.strftime("%Y-%m-%d"), 'status': statuses[problem.status],
                     'problem_creator_email': problem.tenant.email,
                     'treatment_start': "null" if problem.date2 == None else problem.date2.strftime("%Y-%m-%d"),
                     'image': image_str})

        return jsonify(res_for_client), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_problems_by_building', methods=['GET'])
def get_problems_by_building():
    try:
        types = ["", "Electricity", "Plumbing", "infrastructure", "Construction", "Other"]
        statuses = ["", "opened", "in treatment", "solved"]
        data = request.args
        building = Building.objects.get(address=data['address'])
        problems = Problem.objects()
        res_for_client = []
        for problem in problems:
            if problem.building == building and not problem.status == 3:

                path_image = problem.image
                if path_image == "":
                    image_str = ""
                else:
                    img = cv2.imread("./" + path_image)
                    # Define compression parameters
                    compression_params = [cv2.IMWRITE_JPEG_QUALITY, 90]  # Adjust quality as desired (0-100)

                    # Compress the image to JPEG format
                    _, compressed_image = cv2.imencode('.jpg', img, compression_params)

                    # Convert the compressed image to a string in base64 format
                    image_str = base64.b64encode(compressed_image).decode('utf-8')

                res_for_client.append({'id': str(problem.id), 'type': types[problem.type],
                                       'description': problem.description,
                                       'opening_date': problem.date1.strftime("%Y-%m-%d"),
                                       'status': statuses[problem.status],
                                       'problem_creator_email': problem.tenant.email,
                                       'treatment_start': "null" if problem.date2 == None else problem.date2.strftime("%Y-%m-%d"),
                                       'image': image_str})

        return jsonify(res_for_client), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/buildings/update_problem', methods=['POST'])
def update_problem():
    try:
        data = request.args
        problem = Problem.objects.get(id=data["id"])
        if problem.status == 1:
            problem.date2 = datetime.now()
            problem.status = 2
        elif problem.status == 2:
            problem.date3 = datetime.now()
            problem.status = 3
        problem.save()
        return jsonify(problem.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/add_tenant_to_building', methods=['PUT'])
def add_tenant_to_building():
    try:
        data = request.args
        email = data.get('email')
        address = data.get('address')
        user = User.objects.get(email=email)
        building = Building.objects.get(address=address)
        if user in building.tenants:
            return jsonify({'error': 'The tenant is already registered in this building'}), 500
        if user in building.pending_approval_tenants:
            return jsonify({'error': 'The tenant is already pending approval for this building'}), 500

        building.pending_approval_tenants.append(user)
        building.save()
        return jsonify(building.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/buildings/add_survey_to_building', methods=['POST'])
def add_survey_to_building():
    try:
        data = request.args
        address = data.get('address')
        title = data.get('title')
        question = data.get('question')
        list_of_answers = data.get('list_of_answers').split('$')
        deadline = parse(data.get('deadline'))
        survey = Survey(title=title, question=question, deadline=deadline)
        [survey.list_of_answers.append(answer) for answer in list_of_answers]
        survey.save()
        building = Building.objects.get(address=address)
        building.surveys.append(survey)
        building.save()
        return jsonify(survey.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/get_surveys_by_building', methods=['GET'])
def get_surveys_by_building():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        email = data["email"]
        client_date = parse(data['client_date'])
        user = User.objects.get(email=email)
        surveys = building.surveys
        res_for_client = []
        for survey in surveys:
            if survey.deadline > client_date and not (user in [result.user for result in survey.results]):
                res_for_client.append({'title': survey.title, 'deadline': survey.deadline.strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify(res_for_client), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/get_answered_surveys_by_building', methods=['GET'])
def get_answered_surveys():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        email = data["email"]
        client_date = parse(data['client_date'])
        user = User.objects.get(email=email)
        surveys = building.surveys
        res_for_client = []
        building_tenant = set(building.tenants)
        for survey in surveys:
            tenants_answered = set([result.user for result in survey.results])
            if survey.deadline < client_date or building_tenant.issubset(tenants_answered):
                res_for_client.append({'title': survey.title, 'deadline': survey.deadline.strftime("%Y-%m-%d %H:%M:%S")})
        return jsonify(res_for_client), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/get_results', methods=['GET'])
def get_results():
    try:
        data = request.args
        survey = Survey.objects.get(title=data["title"])
        res_for_client = {'question': survey.question, 'results': []}
        for answer in survey.list_of_answers:
            n = len([x for x in survey.results if survey.list_of_answers[x.choice] == answer])
            res_for_client['results'].append({'answer': answer, 'amount': str(n)})

        return jsonify(res_for_client), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/buildings/get_survey_by_title', methods=['GET'])
def get_survey_by_title():
    try:
        data = request.args
        # building = Building.objects.get(address=data["address"])
        # email = data["email"]
        # index = data['index']
        # user = User.objects.get(email=email)
        survey = Survey.objects.get(title=data["title"])
        res_for_client = {'question': survey.question, 'list_of_answers': survey.list_of_answers}
        return jsonify(res_for_client), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/get_parking_slots', methods=['GET'])
def get_parking_slots():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        i = building.index

        # without treads run:
        # check_availability(i)
        # ---------
        building = Building.objects.get(address=data["address"])
        res_for_client = {'amount': str(building.available_parking_amount)}
        return jsonify(res_for_client), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/get_parking_image', methods=['GET'])
def get_parking_image():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        path_image = building.update_parking_image
        if path_image == "":
            image_str = ""
        else:
            img = cv2.imread("./" + building.update_parking_image)
            resized_image = cv2.resize(img, (800, 600), interpolation=cv2.INTER_AREA)
            # Define compression parameters
            compression_params = [cv2.IMWRITE_JPEG_QUALITY, 90]  # Adjust quality as desired (0-100)

            # Compress the image to JPEG format
            _, compressed_image = cv2.imencode('.jpg', resized_image, compression_params)

            # Convert the compressed image to a string in base64 format
            image_str = base64.b64encode(compressed_image).decode('utf-8')
        res_for_client = {'image': image_str}
        return jsonify(res_for_client), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/update_survey', methods=['POST'])
def update_survey():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        email = data["email"]
        survey = Survey.objects.get(title=data["title"])
        choice = data['choice']
        # address = data['address']
        user = User.objects.get(email=email)
        result = Result(user=user, choice=choice)
        result.save()
        survey.results.append(result)
        survey.save()
        if user == building.admin:
            return jsonify(result.to_dict()), 201
        else:
            return jsonify(result.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/remove_tenant_from_building', methods=['Get'])
def remove_tenant_from_building():
    try:
        data = request.args
        email = data.get('email')
        address = data.get('address')
        user = User.objects.get(email=email)
        building = Building.objects.get(address=address)
        if not user == building.admin:
            Building.objects(id=building.id).update_one(pull__tenants=user)
            return jsonify({'message': 'Tenant successfully removed'}), 200

        if user == building.admin:
            if len(building.tenants) == 1:
                Building.objects(id=building.id).update_one(pull__tenants=user)
                building.delete()
                return jsonify({'message': 'You were the only tenant in this building and therefore the building has'
                                           'been removed from the database'}), 200
            else:
                return jsonify({'message': 'choose another admin'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/get_tenants_by_building', methods=['Get'])
def get_tenants_by_building():
    try:
        data = request.args
        address = data.get('address')
        building = Building.objects.get(address=address)
        return jsonify({"tenants": [tenant.email for tenant in building.tenants if not tenant == building.admin]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/update_admin', methods=['Get'])
def update_admin():
    try:
        data = request.args
        address = data.get('address')
        new_email = data.get('new_email')
        building = Building.objects.get(address=address)
        old_admin = building.admin
        new_admin = User.objects.get(email=new_email)
        building.admin = new_admin
        Building.objects(id=building.id).update_one(pull__tenants=old_admin)
        building.save()
        return jsonify({'message': 'admin changed'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@app.route('/Buildings/<string:id>', methods=['PUT'])
def update_Building(id):
    try:
        # Building_data = request.form
        Building_data = request.get_json()
        building = Building.objects.get(id=id)
        Building.name = Building_data.get('name', Building.name)
        if 'user_id' in Building_data:
            user = User.objects.get(id=Building_data['user_id'])
            Building.user_id = user
        Building.save()
        return jsonify(building.to_dict()), 200
    except DoesNotExist:
        return jsonify({'error': 'Building not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid Building ID or user ID'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/Buildings/<string:id>', methods=['DELETE'])
def delete_Building(id):
    try:
        building = Building.objects.get(id=id)
        Building.delete()
        return '', 204
    except DoesNotExist:
        return jsonify({'error': 'Building not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid Building ID'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500




def generate_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


@app.route('/cars/new_car', methods=['POST'])
def add_car():
    try:
        data = request.form
        user = User.objects.get(email=data['email'])
        building = Building.objects.get(address=data['address'])
        if not user in building.tenants:
            return jsonify({'error': 'you are not registered in this building'}), 500
        flag = data['flag']
        car_number = data['car_number']
        if flag == '1':
            image_bytes = base64.b64decode(car_number.replace(" ", "+"))
            image = Image.open(io.BytesIO(image_bytes))
            car_number = licence_plate_recognition(image)
        is_exist = Car.objects(car_number=car_number)
        if is_exist:
            car = Car.objects.get(car_number=car_number)
            if car in building.cars:
                return jsonify({'error': 'This car is already registered in this building'}), 500
            if car in building.pending_approval_cars:
                return jsonify({'error': 'This car is already pending approval for this building'}), 500
        else:
            car = Car(car_number=car_number, owner=user)
            car.save()
        if user in [car.owner for car in building.cars]:
            building.pending_approval_cars.append(car)
            building.save()
            return jsonify(car.to_dict()), 200
        else:
            building.cars.append(car)
            building.save()
            return jsonify(car.to_dict()), 201
    except KeyError:
        return jsonify({'error': 'Missing required field(s)'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/buildings/pending_approval_tenants', methods=['GET'])
def get_pending_approval_tenants():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        res_for_client = []
        for tenant in building.pending_approval_tenants:
            res_for_client.append({'id': str(tenant.id), 'name': tenant.name, 'email': tenant.email})
        return jsonify(res_for_client), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/pending_approval_cars', methods=['GET'])
def get_pending_approval_cars():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        res_for_client = []
        for car in building.pending_approval_cars:
            res_for_client.append({'car_number': car.car_number, 'owner_email': car.owner.email, 'owner_name': car.owner.name})
        return jsonify(res_for_client), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/approve_tenant', methods=['PUT'])
def approve_tenant():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        tenant = User.objects.get(email=data["email"])
        Building.objects(id=building.id).update_one(pull__pending_approval_tenants=tenant)
        if data['ans'] == '1':
            building.tenants.append(tenant)
        building.save()
        return jsonify(building.tenants), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/approve_car', methods=['PUT'])
def approve_car():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        car = Car.objects.get(car_number=data["car_number"])
        Building.objects(id=building.id).update_one(pull__pending_approval_cars=car)
        if data['ans'] == '1':
            building.cars.append(car)
        building.save()
        return jsonify(building.cars), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/amount_of_cars_per_building', methods=['GET'])
def amount_of_cars_per_building():
    try:
        data = request.args
        building = Building.objects.get(address=data["address"])
        res = [car for car in building.cars if car.owner.email == data["email"]]
        return jsonify({"answer": str(len(res))}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500





if __name__ == '__main__':
    # if you want threads - run this:
    # buildings = Building.objects.order_by('index')  # Retrieve all buildings and order them by index
    # print("Starting threads")
    # index = 0
    # if buildings:
    #     print(f'Building length {buildings}')
    #     for building in buildings:
    #         print(f'start thread {index+1}')
    #         index += 1
    #         client_thread = threading.Thread(target=check_availability, args=(building.index,))
    #         client_thread.start()
    #         # threads.append(client_thread)
    #         print(f'Index {index} started.')
    #         # client_thread.join()
    # print("Running app")
    # until here if you want threads

    app.run(port=5000, host='0.0.0.0', debug=True)

    # app.run()


