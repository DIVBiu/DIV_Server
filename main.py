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
    items = db.ListField(db.ReferenceField('Item'))

    def to_dict(self):
        return {'id': str(self.id), 'name': self.name, 'email': self.email, 'password': self.password}


class Item(db.Document):
    name = db.StringField(required=True)
    user_id = db.ReferenceField(User)

    def to_dict(self):
        return {'id': str(self.id), 'name': self.name, 'user_id': str(self.user_id.id)}


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
        email = data.get('email')
        name = data.get('name')
        password = data.get('password')
        user = User(name=data['name'], email=data['email'], password=data['password'])
        user.save()
        return jsonify(user.to_dict()), 201
    except KeyError:
        return jsonify({'error': 'Missing required field(s)'}), 400
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


@app.route('/items', methods=['GET'])
def get_all_items():
    try:
        items = Item.objects()
        return jsonify([item.to_dict() for item in items]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/items/<string:id>', methods=['GET'])
def get_item(id):
    try:
        item = Item.objects.get(id=id)
        return jsonify(item.to_dict()), 200
    except DoesNotExist:
        return jsonify({'error': 'Item not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid item ID'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/items', methods=['POST'])
def create_item():
    try:
        # item_data = request.form
        item_data = request.get_json()
        user_id = item_data.get('user_id')
        user = User.objects.get(id=user_id)
        item = Item(name=item_data['name'], user_id=user)
        user.items.append(item)
        item.save()
        user.save()
        return jsonify(item.to_dict()), 201
    except KeyError:
        return jsonify({'error': 'Missing required field(s)'}), 400
    except DoesNotExist:
        return jsonify({'error': 'User not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid user ID or item name'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/items/<string:id>', methods=['PUT'])
def update_item(id):
    try:
        # item_data = request.form
        item_data = request.get_json()
        item = Item.objects.get(id=id)
        item.name = item_data.get('name', item.name)
        if 'user_id' in item_data:
            user = User.objects.get(id=item_data['user_id'])
            item.user_id = user
        item.save()
        return jsonify(item.to_dict()), 200
    except DoesNotExist:
        return jsonify({'error': 'Item not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid item ID or user ID'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/items/<string:id>', methods=['DELETE'])
def delete_item(id):
    try:
        item = Item.objects.get(id=id)
        item.delete()
        return '', 204
    except DoesNotExist:
        return jsonify({'error': 'Item not found'}), 404
    except ValidationError:
        return jsonify({'error': 'Invalid item ID'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0', debug=True)
    # app.run()


