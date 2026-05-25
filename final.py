import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt, check_password_hash
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv('db.env')

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notebook = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(100))
    content = db.Column(db.Text)

# Routes
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
    username, password = data.get('username'), data.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        return jsonify({"message": "Login successful!", "user_id": user.id}), 200
    else:
        return jsonify({"message": "Invalid credentials"}), 401

@app.route('/api/notes', methods=['GET'])
def get_notes():
    user_id = request.args.get('user_id')
    notes = Note.query.filter_by(user_id=user_id).all()
    response = {"personal": [], "work": [], "ideas": []}
    for note in notes:
        if note.notebook in response:
            response[note.notebook].append({
                "id": note.id, "title": note.title, "content": note.content
            })
    return jsonify(response)

@app.route('/api/notes', methods=['POST'])
def save_notes():
    data = request.get_json()
    user_id = request.args.get('user_id')
    
    # Track IDs we are keeping
    kept_ids = []
    
    for category, notes in data.items():
        for note_data in notes:
            # Check if this is an existing note (ignore very large Date.now() IDs)
            # Assuming real DB IDs are smaller than 1,000,000
            note = None
            if note_data['id'] < 1000000: 
                note = Note.query.filter_by(id=note_data['id'], user_id=user_id).first()
            
            if note:
                note.title = note_data['title']
                note.content = note_data['content']
                note.notebook = category
                kept_ids.append(note.id)
            else:
                # Create a NEW note without relying on the Date.now() ID
                new_note = Note(user_id=user_id, notebook=category, 
                                title=note_data['title'], content=note_data['content'])
                db.session.add(new_note)
                db.session.flush() # Get the new ID from DB
                kept_ids.append(new_note.id)
    
    # Delete notes not present in the current UI state
    Note.query.filter(Note.user_id == user_id, ~Note.id.in_(kept_ids)).delete(synchronize_session=False)
    
    db.session.commit()
    return jsonify({"message": "Notes synchronized!"}), 200


@app.route('/debug/clear-all', methods=['GET'])
def clear_all():
    db.session.query(Note).delete()
    db.session.query(User).delete()
    db.session.commit()
    return "All users and notes deleted!"

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)