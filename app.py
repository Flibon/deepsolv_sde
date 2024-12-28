from flask import Flask, render_template, request, redirect, url_for, session,jsonify,flash,send_file
from models import db, User,Post,Like,Comment,Follow
from werkzeug.utils import secure_filename
import io

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///login.sqlite3'
app.secret_key = 'secret_key' 

db.init_app(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = User(username=data['username'], email=data['email'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully!'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and bcrypt.check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/create_post', methods=['POST'])
@jwt_required()
def create_post():
    data = request.get_json()
    user_id = get_jwt_identity()
    new_post = Post(
        caption=data['caption'],
        image_url=data.get('image_url'),
        video_url=data.get('video_url'),
        music_url=data.get('music_url'),
        category=data['category'],
        user_id=user_id
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify({'message': 'Post created successfully!'}), 201

@app.route('/profile/<int:user_id>', methods=['GET'])
def view_profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user_id).all()
    profile_data = {
        'username': user.username,
        'email': user.email,
        'bio': user.bio,
        'profile_pic': user.profile_pic,
        'posts': [{
            'id': post.id,
            'caption': post.caption,
            'image_url': post.image_url,
            'datetime_posted': post.datetime_posted
        } for post in posts]
    }
    return jsonify(profile_data), 200

@app.route('/follow/<int:user_id>', methods=['POST'])
@jwt_required()
def follow_user(user_id):
    current_user = get_jwt_identity()
    if current_user == user_id:
        return jsonify({'message': 'You cannot follow yourself!'}), 400
    follow = Follow(follower_id=current_user, following_id=user_id)
    db.session.add(follow)
    db.session.commit()
    return jsonify({'message': 'Followed successfully!'}), 201

@app.route('/feed', methods=['GET'])
@jwt_required()
def user_feed():
    current_user = get_jwt_identity()
    follows = Follow.query.filter_by(follower_id=current_user).all()
    following_ids = [follow.following_id for follow in follows]
    posts = Post.query.filter(Post.user_id.in_(following_ids)).order_by(Post.datetime_posted.desc()).all()
    feed = [{
        'id': post.id,
        'caption': post.caption,
        'image_url': post.image_url,
        'datetime_posted': post.datetime_posted
    } for post in posts]
    return jsonify(feed), 200

# Run app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
