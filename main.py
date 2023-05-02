from flask import Flask, jsonify, request
from flask_mongoengine import MongoEngine
from mongoengine.errors import DoesNotExist, ValidationError
from dateutil.parser import parse

app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {
    'db': 'test',
    'host': 'localhost',
    'port': 27017
}
db = MongoEngine(app)



class User(db.Document):
    name = db.StringField(required=True)
    email = db.EmailField(required=True, unique=True)
    password = db.StringField(required=True)
    # buildings = db.ListField(db.ReferenceField('Building'))

    def to_dict(self):
        return {'id': str(self.id), 'name': self.name, 'email': self.email, 'password': self.password}


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

    def to_dict(self):
        return {'id': str(self.id), 'address': self.address, 'tenants': self.tenants, 'chat': self.chat}


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
        return jsonify([t.address for t in Building.objects(tenants__in=[user])]), 200
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


@app.route('/buildings/new_building', methods=['POST'])
def create_Building():
    try:
        data = request.args
        # address = data.get('address')
        building = Building(address=data['address'])
        building.save()
        return jsonify(building.to_dict()), 201
    except KeyError:
        return jsonify({'error': 'Missing required field(s)'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/building/new_problem', methods=['POST'])
def new_problem():
    try:
        data = request.args
        building = Building.objects.get(address=data['address'])
        user = User.objects.get(email=data['email'])
        type = data['type']
        description = data['description']
        client_date = parse(data['date'])
        problem = Problem(type=type, description=description, status=1, tenant=user, date1=client_date, building=building)
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
                # res_for_client.append({'id': str(problem.id), 'type': types[problem.type], 'description': problem.description, 'opening_date': problem.date1.strftime("%Y-%m-%d"), 'status': statuses[problem.status], 'treatment_start': "null" if problem.date2 == None else problem.date2.strftime("%Y-%m-%d")})
                res_for_client.append({'id': str(problem.id), 'type': types[problem.type], 'description': problem.description, 'opening_date': problem.date1.strftime("%Y-%m-%d"), 'status': statuses[problem.status]})

        return jsonify(res_for_client), 200
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
        building.tenants.append(user)
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


@app.route('/buildings/update_survey', methods=['POST'])
def update_survey():
    try:
        data = request.args
        # building = Building.objects.get(address=data["address"])
        email = data["email"]
        survey = Survey.objects.get(title=data["title"])
        choice = data['choice']
        user = User.objects.get(email=email)
        result = Result(user=user, choice=choice)
        result.save()
        survey.results.append(result)
        survey.save()
        return jsonify(result.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/remove_tenant_from_building', methods=['PUT'])
def remove_tenant_from_building():
    try:
        data = request.args
        email = data.get('email')
        address = data.get('address')
        user = User.objects.get(email=email)
        building = Building.objects.get(address=address)
        Building.objects(id=building.id).update_one(pull__tenants=user)
        # if user in building.tenants:
        #     return jsonify({'error': 'The tenant is already registered in this building'}), 500
        # building.tenants.append(user)
        # building.save()
        return jsonify(building.to_dict()), 200
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


if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0', debug=True)
    # app.run()


