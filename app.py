from flask import Flask, render_template, request, redirect, url_for, session,jsonify,flash,send_file
from models import db, User,Post,Like,Comment,Follow
from werkzeug.utils import secure_filename
import io

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///login.sqlite3'
app.secret_key = 'secret_key' 

db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)


import os
from werkzeug.utils import secure_filename

# File upload settings
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit to 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# -------------------------
# Home Page
@app.route('/')
def home():
    posts = Post.query.order_by(Post.datetime_posted.desc()).all()
    feed = []
    for post in posts:
        user = User.query.get(post.user_id)
        feed.append({
            'id': post.id,
            'caption': post.caption,
            'image_url': post.image_url,
            'category': post.category,
            'datetime_posted': post.datetime_posted,
            'username': user.username
        })
    return render_template('home.html', posts=feed)

# -------------------------
# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('User registered successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# -------------------------
# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')

# -------------------------
# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# -------------------------
# Create Post
@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash('Unauthorized! Please log in.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        caption = request.form['caption']
        category = request.form['category']
        user_id = session['user_id']

        # Handle file upload
        file = request.files['image']
        if file and file.filename != '':
            # Check allowed extensions
            if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                # Save the post in the database
                new_post = Post(
                    caption=caption,
                    image_url=file_path,  # Store file path in DB
                    category=category,
                    datetime_posted=datetime.utcnow().isoformat(),
                    user_id=user_id
                )
                db.session.add(new_post)
                db.session.commit()
                flash('Post created successfully!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid file type. Allowed types: png, jpg, jpeg, gif.', 'danger')
        else:
            flash('No file uploaded.', 'danger')

    return render_template('create_post.html')


# -------------------------
# View Profile
@app.route('/profile/<int:user_id>', methods=['GET'])
def view_profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user_id).all()
    return render_template('profile.html', user=user, posts=posts)

@app.route('/feed', methods=['GET'])
def user_feed():
    user_id = session.get('user_id')
    if not user_id:
        flash('Unauthorized! Please log in.', 'danger')
        return redirect(url_for('login'))

    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Get posts from followed users
    follows = Follow.query.filter_by(follower_id=user_id).all()
    following_ids = [follow.following_id for follow in follows]

    posts = Post.query.filter(Post.user_id.in_(following_ids)) \
        .order_by(Post.datetime_posted.desc()) \
        .paginate(page=page, per_page=per_page)

    # Generate URLs for pagination
    next_url = url_for('user_feed', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('user_feed', page=posts.prev_num) if posts.has_prev else None

    return render_template('feed.html', posts=posts.items, next_url=next_url, prev_url=prev_url)


# -------------------------
# Initialize Database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)