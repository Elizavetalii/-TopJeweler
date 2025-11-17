from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/lumieresecrete'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Analytics(db.Model):
    __tablename__ = 'analytics'
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

# Logging configuration
logging.basicConfig(level=logging.INFO)

@app.route('/analytics', methods=['POST'])
def create_event():
    data = request.json
    new_event = Analytics(event_type=data['event_type'], user_id=data['user_id'], timestamp=data['timestamp'])
    try:
        db.session.add(new_event)
        db.session.commit()
        return jsonify({'message': 'Event created successfully'}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'Error creating event'}), 400

@app.route('/analytics', methods=['GET'])
def get_events():
    events = Analytics.query.all()
    return jsonify([{'id': event.id, 'event_type': event.event_type, 'user_id': event.user_id, 'timestamp': event.timestamp} for event in events]), 200

if __name__ == '__main__':
    app.run(debug=True)