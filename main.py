import os
import certifi
import requests
from flask import Flask, Response, jsonify, request, make_response, render_template, flash, redirect, g, after_this_request
from flask_pymongo import PyMongo
from pymongo import MongoClient
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from bson.json_util import dumps
from bson.objectid import ObjectId
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from botocore.exceptions import NoCredentialsError
import boto3

app = Flask(__name__)
jwt = JWTManager(app)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

mongo_db_url = os.environ.get("MONGO_DB_CONN_STRING")
client = MongoClient(mongo_db_url)
db = client['wild-cabarets']

connection_string = f"mongodb://localhost:27017/wildcabarets"
client = MongoClient(connection_string)

app.config['MONGO_URI'] = "mongodb://localhost:27017/wildcabarets"
mongo = PyMongo(app)

# connection_string = f"mongodb+srv://pratyush:76m3t4IY0kqh19p8@superminds-cluster-public-f49e7a24.mongo.ondigitalocean.com/admin?authSource=admin&replicaSet=superminds-cluster-public&tls=true"
# client = MongoClient(connection_string, tlsCAFile=certifi.where())

# app.config['MONGO_URI'] = "mongodb+srv://pratyush:76m3t4IY0kqh19p8@superminds-cluster-public-f49e7a24.mongo.ondigitalocean.com/admin?authSource=admin&replicaSet=superminds-cluster-public&tls=true"
# mongo = PyMongo(app)

# Configure SWAGGER
SWAGGER_URL = '/swagger'  
API_URL = '/static/swagger.json'  # Our API url (can of course be a local resource)

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,  
    API_URL,
    config={ 
        'app_name': "Booking",
    },
)

app.register_blueprint(swaggerui_blueprint, url_prefix = SWAGGER_URL)

auth = HTTPBasicAuth()
# from flasgger import Swagger

# Configure Swagger
# app.config['SWAGGER'] = {
#     'title': 'API Documentation',
#     'uiversion': 3,
#     'specs_route': '/swagger/',
# }

# swagger = Swagger(app)

# # Serve Swagger UI with JWT authentication
# @app.route('/swagger/')
# @jwt_required()  # Protect the Swagger UI endpoint with JWT authentication 
# def serve_swagger_ui():
#     with app.open_resource('/Users/pratyushsharma/booking/static/swagger.json') as f:
#         swagger_spec = f.read()
#         return Response(swagger_spec, mimetype='application/json')

# Configure JWT
app.config['JWT_SECRET_KEY'] = '854d9f0a3a754b16a6e1f3655b3cfbb5'
jwt = JWTManager(app)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcwMTM2MTQwMCwianRpIjoiZGJlZmY2NzAtM2IzMi00NGQ3LTlkNzItMjY2NjliNjA3OGM0IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6InVzZXIxIiwibmJmIjoxNzAxMzYxNDAwLCJleHAiOjE3MDEzNjIzMDB9.Il6UB4Til2jOXTTaMhaFe0SOlhKmNkBQn6S3bdKzRtE'}

# Mock user data for demonstration
users = {
    'user1': {'password': 'password1'},
    "admin": generate_password_hash("admin"),
}

# Token creation route (login)
@app.route('/login', methods=['GET','POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if username in users and users[username]['password'] == password:
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

# Protected route (CRUD operations)
@app.route('/protected', methods=['GET', 'POST'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

# Configure BasicAuth
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

# Base 
@app.route('/')
@auth.login_required
def index():
    return "Hello, {}!".format(auth.current_user())

# Create a User
@app.route('/user', methods=['POST'])
def add_user():
    _json = request.json
    _name = _json['name']
    _email = _json['email']
    _pwd = _json['pwd']

    if _name and _email and _pwd and request.method == 'POST':
        _hashed_password = generate_password_hash(_pwd) 
        id = mongo.db.user.insert_one({'name': _name, 'email': _email, 'pwd': _hashed_password})
        return {"data":"User added successfully"}
    else:
        return {'error':'Not found'}



apis = [
    "http://localhost:8080/bookings",
    "http://localhost:8080/contacts",
    "http://localhost:8080/events",
    "http://localhost:8080/newsletters"
    # Add more endpoints as needed
]

@app.route('/getAllData', methods=['GET'])
def get_aggregated_data():
    aggregated_data = []

    for api in apis:
        try:
            response = requests.get(api)
            data = response.json()
            aggregated_data.append(data)
        except Exception as e:
            aggregated_data.append({"error": str(e)})

    return jsonify(aggregated_data)

# Get all books
@app.route('/bookings', methods=['GET'])
def get_bookings():
    bookings = mongo.db.booking.find()
    resp = dumps(bookings)
    return resp

# Get a specific booking by ID
@app.route('/booking/<id>')
@jwt_required()
def booking(id):
    booking = mongo.db.booking.find_one({'_id':ObjectId(id)})
    resp = dumps(booking)
    return resp

# Delete a booking
@app.route('/booking/<id>', methods=['DELETE'])
@jwt_required()
def delete_booking(id):
    mongo.db.booking.delete_one({'_id':ObjectId(id)})
    resp = jsonify("Booking Deleted Successfully")
    resp.status_code = 200
    return resp

# Update a booking
@app.route('/booking/<id>', methods=['PUT'])
@jwt_required()
def update_booking(id):
    _json = request.json
    _id = id
    _name = _json['name']
    _contactNumber = _json['contactNumber']
    _contactEmail = _json['contactEmail']
    _showDate = _json['showDate']
    _numberOfGuests = _json['numberOfGuests']
    _dietaryRequirements = _json['dietaryRequirements']
    _message = _json['message']

    if _name and _contactNumber and _contactEmail and _showDate and _numberOfGuests and _dietaryRequirements and _message and request.method == 'PUT':
        mongo.db.booking.update_one({'_id': ObjectId(_id['$oid']) if '$oid' in _id else ObjectId(_id)}, {'$set': {'name': _name, 'contactNumber': _contactNumber, 'contactEmail': _contactEmail, 'showDate': _showDate, 'numberOfGuests': _numberOfGuests, 'dietaryRequirements': _dietaryRequirements, 'message':  _message }})
        resp = jsonify("Booking Updated Successfully")
        resp.status_code = 200
        return resp

# Create a booking
@app.route('/bookings', methods=['POST'])
@jwt_required()
def create_booking():
    _json = request.json
    _name = _json['name']
    _contactNumber = _json['contactNumber']
    _contactEmail = _json['contactEmail']
    _showDate = _json['showDate']
    _numberOfGuests = _json['numberOfGuests']
    _dietaryRequirements = _json['dietaryRequirements']
    _message = _json['message']

    if _name and _contactNumber and _contactEmail and _showDate and _numberOfGuests and _dietaryRequirements and _message and request.method == 'POST':
        id = mongo.db.booking.insert_one({'name': _name, 'contactNumber': _contactNumber, 'contactEmail': _contactEmail, 'showDate': _showDate, 'numberOfGuests': _numberOfGuests, 'dietaryRequirements': _dietaryRequirements, 'message':  _message })
        return {"data":"Booking Added Successfully"}
    else:
        return {'error':'Booking Not Found'}


# wildcabarets = client.wildcabarets
# booking_collection= wildcabarets.booking_collection

# bookings = [
#     {
#         'id': 1,
#         'Name':'Fabio',
#         'ContactNumber': 9999988888,
#         'ContactEmail': 'fabio@superminds.dev',
#         'ShowDate': '02.02.2024',
#         'NumberOfGuests': '10',
#         'DietaryRequirements': '5',
#         'Message': 'BlessUs'
#     }
# ]

# # Create a booking
# @app.route('/bookings', methods=['POST'])
# def create_booking():
#     # new_booking={'id':len(book_now)+1, 'Name':request.json['Name'], 'ContactNumber':request.json['ContactNumber'], 'ContactEmail': request.json['ContactEmail'], 'ShowDate': request.json['ShowDate'], 'NumberOfGuests': request.json['NumberOfGuests'], 'DietaryRequirements': request.json['DietaryRequirements'], 'Message': request.json['Message'] }
#     # book_now.append(new_booking)
#     # return new_booking

# # Update a booking
# @app.route('/bookings/<int:book_id>', methods=['PUT'])
# def update_booking(book_id):
#     for booking in bookings:
#         if booking['id']==book_id:
#             booking['Name']=request.json['Name']
#             booking['ContactNumber']=request.json['ContactNumber']
#             booking['ContactEmail']=request.json['ContactEmail']
#             booking['ShowDate']=request.json['ShowDate']
#             booking['NumberOfGuests']=request.json['NumberOfGuests']
#             booking['DietaryRequirements']=request.json['DietaryRequirements']
#             booking['Message']=request.json['Message']
#             return booking 
#     return {'error':'Booking not found'}

# # Get all books
# @app.route('/bookings', methods=['GET'])
# def get_bookings():
#     return bookings

# # Get a specific booking by ID
# @app.route('/book_now/<int:book_id>', methods=['GET'])
# def get_booking(book_id):
#     for booking in book_now:
#         if booking['id']==book_id:
#             return booking

#     return {'error':'Booking not found'}

# # Delete a booking
# @app.route('/bookings/<int:book_id>', methods=['DELETE'])
# def delete_booking(book_id):
#     for booking in bookings:
#         if booking['id']==book_id:
#             bookings.remove(booking)
#             return {"data":"Booking Deleted Successfully"}

#     return {'error':'Booking Not Found'}

# # Create a booking
# @app.route('/book_now', methods=['POST'])
# def create_booking():
#     Names = ["Pratyush", "Rahul"]
#     ContactNumbers = ["9667279794", "8860600257"]
#     ContactEmails = ["pratyush@superminds.dev", "rahul@superminds.dev"]
#     Showdates = ["01.01.2020", "09.09.2023"]
#     NumberOfGuests = ["4", "7"]
#     DietaryRequirements = ["100", "20"]
#     Messages = ["Bless", "F"]

#     bookings = []

#     for Name, ContactNumber, ContactEmail, Showdate, NumberOfGuest, DietaryRequirement, Message  in zip(Names, ContactNumbers, ContactEmails, Showdates, NumberOfGuests, DietaryRequirements, Messages ):
#         booking ={"Name": Name, "ContactNumber": ContactNumber, "ContactEmail": ContactEmail, "Showdate": Showdate, "NumberOfGuest": NumberOfGuest, "DietaryRequirement": DietaryRequirement, "Message": Message}
#         bookings.append(booking)
        
#     booking_collection.insert_many(bookings)
#     return {'data':'Booking Created Successfully'}

# Get all contacts
@app.route('/contacts', methods=['GET'])
def get_contacts():
    contacts = mongo.db.contact.find()
    resp = dumps(contacts)
    return resp

# Get a specific contact by ID
@app.route('/contact/<id>')
@jwt_required()
def contact(id):
    contact = mongo.db.contact.find_one({'_id':ObjectId(id)})
    resp = dumps(contact)
    return resp

# Delete a contact
@app.route('/contact/<id>', methods=['DELETE'])
@jwt_required()
def delete_contact(id):
    mongo.db.contact.delete_one({'_id':ObjectId(id)})
    resp = jsonify("Contact Deleted Successfully")
    resp.status_code = 200
    return resp

# Update a contact
@app.route('/contact/<id>', methods=['PUT'])
@jwt_required()
def update_contact(id):
    _json = request.json
    _id = id
    _name = _json['name']
    _contactNumber = _json['contactNumber']
    _contactEmail = _json['contactEmail']
    _showDate = _json['showDate']
    _numberOfGuests = _json['numberOfGuests']
    _dietaryRequirements = _json['dietaryRequirements']
    _message = _json['message']

    if _name and _contactNumber and _contactEmail and _showDate and _numberOfGuests and _dietaryRequirements and _message and request.method == 'PUT':
        mongo.db.contact.update_one({'_id': ObjectId(_id['$oid']) if '$oid' in _id else ObjectId(_id)}, {'$set': {'name': _name, 'contactNumber': _contactNumber, 'contactEmail': _contactEmail, 'showDate': _showDate, 'numberOfGuests': _numberOfGuests, 'dietaryRequirements': _dietaryRequirements, 'message':  _message }})
        resp = jsonify("Contact Updated Successfully")
        resp.status_code = 200
        return resp

# Create a contact
@app.route('/contacts', methods=['POST'])
@jwt_required
def create_contact():
    _json = request.json
    _name = _json['name']
    _contactNumber = _json['contactNumber']
    _contactEmail = _json['contactEmail']
    _showDate = _json['showDate']
    _numberOfGuests = _json['numberOfGuests']
    _dietaryRequirements = _json['dietaryRequirements']
    _message = _json['message']

    if _name and _contactNumber and _contactEmail and _showDate and _numberOfGuests and _dietaryRequirements and _message and request.method == 'POST':
        id = mongo.db.contact.insert_one({'name': _name, 'contactNumber': _contactNumber, 'contactEmail': _contactEmail, 'showDate': _showDate, 'numberOfGuests': _numberOfGuests, 'dietaryRequirements': _dietaryRequirements, 'message':  _message })
        return {"data":"Contact Added Successfully"}
    else:
        return {'error':'Contact Not Found'}


# contact_us = [
#     {
#         'id': 1,
#         'Name':'Fabio',
#         'ContactNumber': 9999988888,
#         'ContactEmail': 'fabio@superminds.dev',
#         'ShowDate': '02.02.2024',
#         'NumberOfGuests': '10',
#         'DietaryRequirements': '5',
#         'Message': 'BlessUs'
#     }
# ]

# # Get all contacts
# @app.route('/contact_us', methods=['GET'])
# def get_contact_us():
#     return contact_us


# # Get a specific contact by ID
# @app.route('/contact_us/<int:contactid>', methods=['GET'])
# def get_contact(contactid):
#     for contact in contact_us:
#         if contact['id']==contactid:
#             return contact

#     return {'error':'Contact not found'}

# # Create a contact
# @app.route('/contact_us', methods=['POST'])
# def create_contact():
#     new_contact={'id':len(contact_us)+1, 'Name':request.json['Name'], 'ContactNumber':request.json['ContactNumber'], 'ContactEmail': request.json['ContactEmail'], 'ShowDate': request.json['ShowDate'], 'NumberOfGuests': request.json['NumberOfGuests'], 'DietaryRequirements': request.json['DietaryRequirements'], 'Message': request.json['Message'] }
#     contact_us.append(new_contact)
#     return new_contact


# # Update a contact
# @app.route('/contact_us/<int:contactid>', methods=['PUT'])
# def update_contact(contactid):
#     for contact in contact_us:
#         if contact['id']==contactid:
#             contact['Name']=request.json['Name']
#             contact['ContactNumber']=request.json['ContactNumber']
#             contact['ContactEmail']=request.json['ContactEmail']
#             contact['ShowDate']=request.json['ShowDate']
#             contact['NumberOfGuests']=request.json['NumberOfGuests']
#             contact['DietaryRequirements']=request.json['DietaryRequirements']
#             contact['Message']=request.json['Message']
#             return contact 
#     return {'error':'Contact not found'}

# # Delete a contact
# @app.route('/contact_us/<int:contactid>', methods=['DELETE'])
# def delete_contact(contactid):
#     for contact in contact_us:
#         if contact['id']==contactid:
#             contact_us.remove(contact)
#             return {"data":"Contact Deleted Successfully"}


#     return {'error':'Contact not found'}

# Get all events
@app.route('/events', methods=['GET'])
def get_events():
    events = mongo.db.event.find()
    resp = dumps(events)
    return resp

# Get a specific event by ID
@app.route('/event/<id>')
@jwt_required()
def event(id):
    event = mongo.db.event.find_one({'_id':ObjectId(id)})
    resp = dumps(event)
    return resp

# Delete a event
@app.route('/event/<id>', methods=['DELETE'])
@jwt_required()
def delete_event(id):
    mongo.db.event.delete_one({'_id':ObjectId(id)})
    resp = jsonify("Event Deleted Successfully")
    resp.status_code = 200
    return resp

# Update a event
@app.route('/event/<id>', methods=['PUT'])
@jwt_required()
def update_event(id):
    _json = request.json
    _id = id
    _amount = _json['amount']
    _childAmount = _json['childAmount']
    _date = _json['date']
    _deposit = _json['deposit']
    _description = _json['description']
    _imageURL = _json['imageURL']
    _meals = _json['meals']
    _reservationsStartAt = _json['reservationsStartAt']
    _reservationsEndsAt = _json['reservationsEndsAt']
    _showStarts = _json['showStarts']
    _status = _json['status']
    _title = _json['title']

    if _amount and _childAmount and _date and _deposit and _description and _imageURL and _meals and _reservationsStartAt and _reservationsEndsAt and _showStarts and _status and _title and request.method == 'PUT':
        mongo.db.event.update_one({'_id': ObjectId(_id['$oid']) if '$oid' in _id else ObjectId(_id)}, {'$set': {'amount': _amount, 'childAmount': _childAmount, 'date': _date, 'deposit': _deposit, 'description': _description, 'imageURL': _imageURL, 'meals':  _meals, 'reservationsStartAt': _reservationsStartAt, 'reservationsEndsAt': _reservationsEndsAt, 'showStarts': _showStarts, 'status': _status, 'title': _title }})
        resp = jsonify("Event Updated Successfully")
        resp.status_code = 200
        return resp

# Create an event
@app.route('/events', methods=['POST'])
@jwt_required()
def create_event():
    _json = request.json
    _amount = _json['amount']
    _childAmount = _json['childAmount']
    _date = _json['date']
    _deposit = _json['deposit']
    _description = _json['description']
    _imageURL = _json['imageURL']
    _meals = _json['meals']
    _reservationsStartAt = _json['reservationsStartAt']
    _reservationsEndsAt = _json['reservationsEndsAt']
    _showStarts = _json['showStarts']
    _status = _json['status']
    _title = _json['title']

    if _amount and _childAmount and _date and _deposit and _description and _imageURL and _meals and _reservationsStartAt and _reservationsEndsAt and _showStarts and _status and _title and request.method == 'POST':
        id = mongo.db.event.insert_one({'amount': _amount, 'childAmount': _childAmount, 'date': _date, 'deposit': _deposit, 'description': _description, 'imageURL': _imageURL, 'meals':  _meals, 'reservationsStartAt': _reservationsStartAt, 'reservationsEndsAt': _reservationsEndsAt, 'showStarts': _showStarts, 'status': _status, 'title': _title })
        return {"data":"Event Added Successfully"}
    else:
        return {'error':'Event Not Found'}


# events = [
#     {
#         'id': 1,
#         'amount': 100,
#         'childAmount': 100,
#         'date': '02.02.2024',
#         'deposit': 9999988888,
#         'description': 'Nice event',
#         'imageURL':'www.xyz.com',
#         'meals': '10',
#         'reservationsStartAt': '5',
#         'reservationsEndsAt': '9',
#         'showStarts' : '4',
#         'status' : 'cancelled',
#         'title': 'event'
#     }
# ]

# # Get all events
# @app.route('/events', methods=['GET'])
# def get_events():
#     return events


# # Get a specific event by ID
# @app.route('/events/<int:eventid>', methods=['GET'])
# def get_event(eventid):
#     for event in events:
#         if event['id']==eventid:
#             return event

#     return {'error':'Event not found'}

# # Create an event
# @app.route('/events', methods=['POST'])
# def create_event():
#     new_event={'id':len(events)+1, 'amount':request.json['amount'], 'childAmount':request.json['childAmount'], 'date': request.json['date'], 'deposit': request.json['deposit'], 'description': request.json['description'], 'imageURL': request.json['imageURL'], 'meals': request.json['meals'], 'reservationsStartAt': request.json['reservationsStartAt'], 'reservationsEndsAt': request.json['reservationsEndsAt'],'showStarts': request.json['showStarts'], 'status': request.json['status'], 'title': request.json['title'] }
#     events.append(new_event)
#     return new_event


# UPLOAD_FOLDER = '/Users/pratyushsharma/booking'
# DigitalOcean Spaces configurations
DO_SPACES_ENDPOINT = 'https://wild-cabarets.fra1.digitaloceanspaces.com'  # Replace with your Space URL
DO_ACCESS_KEY = 'DO00FVYZELDGLP9XU3Y4'  # Replace with your DigitalOcean Spaces access key
DO_SECRET_KEY = '3SuOMJtlfNklPrhwv9U3FmkgnhVXbKU+u3fGG1zaZ/g'  # Replace with your DigitalOcean Spaces secret key
DO_BUCKET_NAME = 'wild-cabarets'  # Replace with your DigitalOcean Spaces bucket name

# Create a connection to DigitalOcean Spaces
s3 = boto3.client('s3', endpoint_url=DO_SPACES_ENDPOINT, aws_access_key_id=DO_ACCESS_KEY, aws_secret_access_key=DO_SECRET_KEY)

# Create an event image
@app.route('/events/image', methods=['POST'])
@jwt_required()
def upload_image():
    try:
        # Get the file from the request
        file = request.files['file']

        # Upload the file to DigitalOcean Spaces
        s3.upload_fileobj(file, DO_BUCKET_NAME, file.filename)

        # Get the public URL of the uploaded file
        file_url = f"{DO_SPACES_ENDPOINT}/{DO_BUCKET_NAME}/{file.filename}"

        return jsonify({'message': 'Image uploaded successfully', 'file_url': file_url})
    except NoCredentialsError:
        return jsonify({'error': 'Credentials not available. Check your DigitalOcean Spaces access key and secret key.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Delete an event image
@app.route('/events/image/<string:filename>', methods=['DELETE'])
@jwt_required()
def delete(filename):
        try:
            # Delete the file from DigitalOcean Spaces
            s3.delete_object(Bucket= DO_BUCKET_NAME, Key=filename)

            return {'message': f'File {filename} deleted successfully'}

        except NoCredentialsError:
            return {'error': 'Credentials not available'}

# # Update an event
# @app.route('/events/<int:eventid>', methods=['PUT'])
# def update_event(eventid):
#     for event in events:
#         if event['id']==eventid:
#             event['amount'] =request.json['amount'], 
#             event['childAmount']=request.json['childAmount'], 
#             event['date']= request.json['date'], 
#             event['deposit']= request.json['deposit'], 
#             event['description']= request.json['description'], 
#             event['imageURL']= request.json['imageURL'], 
#             event['meals']= request.json['meals'],
#             event['reservationsStartAt'] = request.json['reservationsStartAt'], 
#             event['reservationsEndsAt']= request.json['reservationsEndsAt'],
#             event['showStarts']= request.json['showStarts'],
#             event['status']= request.json['status'], 
#             event['title']= request.json['title']
#             return  
#     return {'error':'Event not found'}

# # Delete an event
# @app.route('/events/<int:eventid>', methods=['DELETE'])
# def delete_event(eventid):
#     for event in events:
#         if event['id']==eventid:
#             events.remove(event)
#             return {"data":"Event Deleted Successfully"}

#     return {'error':'Event not found'}

# Get all newsletters
@app.route('/newsletters', methods=['GET'])
def get_newsletters():
    newsletters = mongo.db.newsletter.find()
    resp = dumps(newsletters)
    return resp

# Get a specific newsletter by ID
@app.route('/newsletter/<id>')
@jwt_required()
def newsletter(id):
    newsletter = mongo.db.newsletter.find_one({'_id':ObjectId(id)})
    resp = dumps(newsletter)
    return resp

# Delete a newsletter
@app.route('/newsletter/<id>', methods=['DELETE'])
@jwt_required()
def delete_newsletter(id):
    mongo.db.newsletter.delete_one({'_id':ObjectId(id)})
    resp = jsonify("Newsletter Deleted Successfully")
    resp.status_code = 200
    return resp

# Update a newsletter
@app.route('/newsletter/<id>', methods=['PUT'])
@jwt_required()
def update_newsletter(id):
    _json = request.json
    _id = id
    _email = _json['email']

    if _email and request.method == 'PUT':
        mongo.db.newsletter.update_one({'_id': ObjectId(_id['$oid']) if '$oid' in _id else ObjectId(_id)}, {'$set': {'email': _email }})
        resp = jsonify("Newsletter Updated Successfully")
        resp.status_code = 200
        return resp

# Create a newsletter
@app.route('/newsletters', methods=['POST'])
@jwt_required()
def create_newsletter():
    _json = request.json
    _email = _json['email']

    if _email and request.method == 'POST':
        id = mongo.db.newsletter.insert_one({'email': _email })
        return {"data":"Newsletter Added Successfully"}
    else:
        return {'error':'Newsletter Not Found'}


# newsletter_signup = [
#     {
#         'id': 1,
#         'Email': 'fabio@superminds.dev'
#     }
# ]

# # Get all newsletters
# @app.route('/newsletter_signup', methods=['GET'])
# def get_newsletter_signup():
#     return newsletter_signup


# # Get a specific newsletter by ID
# @app.route('/newsletter_signup/<int:newsletterid>', methods=['GET'])
# def get_newslettersignup(newsletterid):
#     for signup in newsletter_signup:
#         if signup['id']==newsletterid:
#             return signup

#     return {'error':'Newsletter Signup not found'}

# # Create a newsletter
# @app.route('/newsletter_signup', methods=['POST'])
# def create_newslettersignup():
#     new_signup={'id':len(newsletter_signup)+1,'Email': request.json['Email'] }
#     newsletter_signup.append(new_signup)
#     return new_signup


# # Update a newsletter
# @app.route('/newsletter_signup/<int:newsletterid>', methods=['PUT'])
# def update_newslettersignup(newsletterid):
#     for signup in newsletter_signup:
#         if signup['id']==newsletterid:            
#             signup['Email']=request.json['Email']
#             return signup 
#     return {'error':'signup not found'}

# # Delete a newsletter
# @app.route('/newsletter_signup/<int:newsletterid>', methods=['DELETE'])
# def delete_newslettersignup(newsletterid):
#     for signup in newsletter_signup:
#         if signup['id']==newsletterid:
#             newsletter_signup.remove(signup)
#             return {"data":"Signup Deleted Successfully"}

#     return {'error': 'Signup not found'}


# Run the flask App
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)