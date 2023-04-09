from flask import Flask, jsonify, request
from flask_mongoengine import MongoEngine
from mongoengine.errors import DoesNotExist, ValidationError

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


class Building(db.Document):
    address = db.StringField(required=True, unique=True)
    tenants = db.ListField(db.ReferenceField('User'))

    def to_dict(self):
        return {'id': str(self.id), 'address': self.address, 'tenants': self.tenants}


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
        return jsonify({'error': str(e)}), 500


@app.route('/buildings/remove_tenant_to_building', methods=['PUT'])
def remove_tenant_to_building():
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


