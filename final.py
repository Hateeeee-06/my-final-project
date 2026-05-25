import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv('db.env')

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username, password = data.get('username'), data.get('password')
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "User already exists!"}), 400
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.add(User(username=username, password_hash=hashed_password))
    db.session.commit()
    return jsonify({"message": "User created successfully!"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if user and bcrypt.check_password_hash(user.password_hash, data.get('password')):
        return jsonify({"message": "Login successful!", "user_id": user.id}), 200
    return jsonify({"message": "Invalid credentials"}), 401
# Model for the notes
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notebook = db.Column(db.String(50), nullable=False) # personal, work, etc.
    title = db.Column(db.String(100))
    content = db.Column(db.Text)

@app.route('/api/notes', methods=['GET'])
def get_notes():
    user_id = request.args.get('user_id') # We'll send this from the frontend
    notes = Note.query.filter_by(user_id=user_id).all()
    
    # Organize notes into categories for your frontend
    response = {"personal": [], "work": [], "ideas": []}
    for note in notes:
        if note.notebook in response:
            response[note.notebook].append({
                "id": note.id, "title": note.title, "content": note.content
            })
    return jsonify(response)

@app.route('/api/notes', methods=['POST'])
def save_notes():
    data = request.get_json() # This expects the whole notebook structure
    user_id = request.args.get('user_id')
    
    # Loop through categories (personal, work, etc.)
    for category, notes in data.items():
        for note_data in notes:
            note = Note.query.filter_by(id=note_data['id']).first()
            if note:
                note.title = note_data['title']
                note.content = note_data['content']
            else:
                new_note = Note(user_id=user_id, notebook=category, 
                                title=note_data['title'], content=note_data['content'])
                db.session.add(new_note)
    db.session.commit()
    return jsonify({"message": "Notes saved to database!"}), 200

with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)