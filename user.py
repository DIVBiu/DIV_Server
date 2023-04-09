# from flask import Flask, jsonify, request
# from flask_mongoengine import MongoEngine
# from mongoengine.errors import DoesNotExist, ValidationError
#
# class User(db.Document):
#     name = db.StringField(required=True)
#     email = db.EmailField(required=True, unique=True)
#     password = db.StringField(required=True)
#     items = db.ListField(db.ReferenceField('Item'))
#
#     def to_dict(self):
#         return {'id': str(self.id), 'name': self.name, 'email': self.email, 'password': self.password}