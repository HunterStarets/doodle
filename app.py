from flask import Flask, render_template, request, abort, redirect, session, url_for, jsonify
from flask_bcrypt import Bcrypt
from datetime import datetime

from src.repositories.user_repository import user_repository_singleton
from src.repositories.post_repository import post_repository_singleton
from src.repositories.comment_repository import comment_repository_singleton
from src.repositories.vote_repostory import vote_repository_singleton
from src.models import db

from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)


# DB connection
if os.getenv("ENV") == 'testing':
   app.config['SQLALCHEMY_DATABASE_URI'] = \
    f'postgresql://{os.getenv("DB_TEST_USER")}:{os.getenv("DB_TEST_PASS")}@{os.getenv("DB_TEST_HOST")}:{os.getenv("DB_TEST_PORT")}/{os.getenv("DB_TEST_NAME")}'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = \
    f'postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASS")}@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}'
    
app.config['SQLALCHEMY_ECHO'] = True
db.init_app(app)

# Bcrypt connection
app.secret_key = os.getenv('APP_SECRET_KEY', 'super-secure')
bcrypt = Bcrypt(app)

# Home page
@app.route('/')
def index():
    user = None
    if 'user_id' in session:
        user = user_repository_singleton.get_user_by_id(session.get('user_id'))    
    posts = post_repository_singleton.get_all_posts()
    posts = sort_posts_newest_to_oldest(posts)
    return render_template('index.html', home_active=True, user=user, posts=posts, user_repository_singleton=user_repository_singleton, vote_repository_singleton= vote_repository_singleton)

# User sign up
@app.get('/signup')
def get_signup_form():
    if 'user_id' in session and 'username' in session:
        return redirect('/')
    return render_template('signup.html')

@app.post('/signup')
def signup():
    email = request.form.get('email')
    username = request.form.get('username')
    raw_password = request.form.get('password')
    first_name = request.form.get('first-name')
    last_name = request.form.get('last-name')
    bio = request.form.get('bio')

    if not (email and username and raw_password and first_name and last_name and bio): 
        abort(400)

    existing_email = user_repository_singleton.get_user_by_email(email)
    if existing_email:
        abort(400)

    existing_username = user_repository_singleton.get_user_by_username(username)
    if existing_username:
        abort(400)

    hashed_password = bcrypt.generate_password_hash(raw_password, 12).decode()

    new_user = user_repository_singleton.create_user(email, username, hashed_password, first_name, last_name, bio)
    session['user_id'] = new_user.user_id
    session['username'] = username
    return redirect('/')

# Login user
@app.post('/login')
def login():
    username = request.form.get('username')
    raw_password = request.form.get('password')
    if not (username and raw_password):   
        abort(400)

    existing_user = user_repository_singleton.get_user_by_username(username)
    if not existing_user: 
        abort(401)

    if not bcrypt.check_password_hash(existing_user.password, raw_password):
        abort(401)

    session['user_id'] = existing_user.user_id
    session['username'] = username
    return redirect('/')

# Logout user
@app.post('/logout')
def logout():
    del session['user_id']
    del session['username']
    return redirect('/')

# Edit user
@app.get('/users/<int:user_id>/edit')
def edit_user_form(user_id: int):
    if 'user_id' not in session and 'username' not in session:
        abort(401)
    if session.get('user_id') != user_id:
        abort(403)
    existing_user = user_repository_singleton.get_user_by_id(user_id)
    if not existing_user:
        abort(404)
    return render_template('edit_user_form.html', existing_user=existing_user)

@app.post('/users/<int:user_id>')
def edit_user(user_id: int):
    email = request.form.get('email')
    username = request.form.get('username')
    current_password = request.form.get('current-password')
    new_password = request.form.get('new-password')
    first_name = request.form.get('first-name')
    last_name = request.form.get('last-name')
    bio = request.form.get('bio')

    if not(email and username and current_password and new_password and first_name and last_name and bio): 
        abort(400)

    existing_user = user_repository_singleton.get_user_by_id(user_id)
    if not existing_user:
        abort(401)

    if email != existing_user.email: 
        existing_email = user_repository_singleton.get_user_by_email(email)
        if existing_email:
            abort(400)

    if username != existing_user.username:
        existing_username = user_repository_singleton.get_user_by_username(username)
        if existing_username:
            abort(400)

    if not bcrypt.check_password_hash(existing_user.password, current_password):
        abort(401)
    hashed_password = bcrypt.generate_password_hash(new_password, 12).decode()

    user_repository_singleton.edit_user(existing_user, email, username, hashed_password, first_name, last_name, bio)
    return redirect('/')

# Delete User
@app.get('/users/<int:user_id>/delete')
def delete_user_form(user_id: int):
    if 'user_id' not in session and 'username' not in session:
        abort(401)
    if session.get('user_id') != user_id:
        abort(403)
    existing_user = user_repository_singleton.get_user_by_id(user_id)
    if not existing_user:
        abort(404)
    return render_template('delete_user_form.html', existing_user=existing_user)

@app.post('/users/<int:user_id>/delete')
def delete_user(user_id: int):
    username = request.form.get('username')
    password = request.form.get('password')
    checkbox = request.form.get('checkbox')

    if not(username and password and checkbox):
        abort(400)
    
    existing_user = user_repository_singleton.get_user_by_username(username)
    if not existing_user: 
        abort(401)

    if not bcrypt.check_password_hash(existing_user.password, password):
        abort(401)

    user_repository_singleton.delete_user(existing_user)
    del session['username']
    del session['user_id']
    return redirect('/')

#TODO: Expand so that anyone can input 
#TODO: Maybe consolodate the nexy 4 routes into one, or at least consolodate upvoted and downvoted route
@app.get('/users/<int:user_id>')
def get_user(user_id: int):
    user = None
    if user_id:
        user = user_repository_singleton.get_user_by_id(user_id)

    if not user:
        abort(401)

    posts= post_repository_singleton.get_all_posts_by_author_id(user_id)
    posts = sort_posts_newest_to_oldest(posts)
    return render_template('view_profile.html', view_profile_active=True, user=user, posts=posts, vote_repository_singleton=vote_repository_singleton, user_repository_singleton=user_repository_singleton)
    
@app.get('/users/<int:user_id>/comments')
def get_user_comments(user_id: int):
    user = None
    if user_id:
        user = user_repository_singleton.get_user_by_id(user_id)

    if not user:
        abort(401)

    user_comments=comment_repository_singleton.get_comments_for_user(user.user_id)
    user_comments = sort_posts_newest_to_oldest(user_comments)
    return render_template('user_comments_only.html',view_profile_active=True,user=user,user_comments=user_comments, user_repository_singleton=user_repository_singleton, vote_repository_singleton=vote_repository_singleton)

@app.get('/users/<int:user_id>/upvoted')
def get_user_upvoted(user_id: int):
        user = None
        if user_id:
            user = user_repository_singleton.get_user_by_id(user_id)

        if not user:
            abort(401)

        post_ids = set()
        upvotes = vote_repository_singleton.get_post_upvotes_by_user_id(user_id)
        for upvote in upvotes:
            post_ids.add(upvote.post_id)

        posts = post_repository_singleton.get_posts_by_ids(post_ids)
        posts = sort_posts_newest_to_oldest(posts)

        return render_template('view_profile.html', view_profile_active=True, user=user, posts=posts, vote_repository_singleton=vote_repository_singleton, user_repository_singleton=user_repository_singleton)

@app.get('/users/<int:user_id>/downvoted')
def get_user_downvoted(user_id: int):
        user = None
        if user_id:
            user = user_repository_singleton.get_user_by_id(user_id)

        if not user:
            abort(401)

        post_ids = set()
        downvotes = vote_repository_singleton.get_post_downvotes_by_user_id(user_id)
        for downvote in downvotes:
            post_ids.add(downvote.post_id)

        posts = post_repository_singleton.get_posts_by_ids(post_ids)
        posts = sort_posts_newest_to_oldest(posts)


        return render_template('view_profile.html', view_profile_active=True, user=user, posts=posts, vote_repository_singleton=vote_repository_singleton, user_repository_singleton=user_repository_singleton)

# Search users
#Reference: module-15-assignment
@app.get('/users/search')
def search_users():
    user = None
    if 'user_id' in session:
        user = user_repository_singleton.get_user_by_id(session.get('user_id'))    
    found_user = None
    q = request.args.get('q', '')
    if q != '':
        found_user = user_repository_singleton.search_users(q)
    return render_template('search_users.html', user=user, found_user=found_user)

# Create posts
@app.get('/posts/new')
def create_post_form():
    if 'user_id' not in session and 'username' not in session:
        abort(401)
    return render_template('create_post_form.html')

# FIX: needs to redirect to users profile
@app.post('/posts')
def create_post():
    title = request.form.get('title')
    content = request.form.get('content')
    community_name = request.form.get('community-name')
    timestamp = datetime.utcnow()
    if not (title and content and community_name):
        abort(400)

    user_id = session.get('user_id')
    user = user_repository_singleton.get_user_by_id(user_id)

    if not (user_id and user):    
        abort(401)
    author_id = user.user_id

    new_post = post_repository_singleton.create_post(title, content, community_name, timestamp, author_id)
    new_post_id = new_post.post_id
    return redirect(f'/posts/{new_post_id}')

# Edit post
@app.get('/posts/<int:post_id>/edit')
def edit_post_form(post_id: int):
    if 'user_id' not in session and 'username' not in session:
        abort(401)
    existing_post = post_repository_singleton.get_post_by_id(post_id)
    if not existing_post:
        abort(404)
    if existing_post.author_id != session.get('user_id'):
        abort(403)
    return render_template('edit_post_form.html', existing_post=existing_post)

@app.post('/posts/<int:post_id>')
def edit_post(post_id: int):
    title = request.form.get('title')
    content = request.form.get('content')
    community_name = request.form.get('community-name')
    if not (title and content and community_name):
        abort(400)

    existing_post = post_repository_singleton.get_post_by_id(post_id)
    if not existing_post:
        abort(401)

    post_repository_singleton.edit_post(existing_post, title, content, community_name)
    return redirect(url_for('get_single_post', post_id=post_id))

# Delete post
@app.post('/posts/<int:post_id>/delete')
def delete_post(post_id: int):
    post_to_delete = post_repository_singleton.get_post_by_id(post_id)
    if not post_to_delete:
        abort(404)
    
    post_repository_singleton.delete_post(post_to_delete)
    return redirect('/')

# View single post
@app.get('/posts/<int:post_id>')
def get_single_post(post_id:int):
    scroll_to_comments = request.args.get('scroll_to_comments', 'false').lower() == 'true'
    reply_to_post = request.args.get('reply_to_post', 'false').lower() == 'true'
    
    existing_post = post_repository_singleton.get_post_by_id(post_id)
    if not existing_post:
        abort(404)
    author = user_repository_singleton.get_user_by_id(existing_post.author_id)
    if not author:
        abort(404)

    existing_post.comments = sort_posts_newest_to_oldest(existing_post.comments)
    return render_template('get_single_post.html', vote_repository_singleton=vote_repository_singleton, existing_post=existing_post, author=author, scrollToComments=scroll_to_comments, replyToPost=reply_to_post)

# Create comment
@app.post('/comments')
def create_comment():
    content = request.form.get('comment-content')
    post_id = request.form.get('post-id')
    timestamp = datetime.utcnow()
    if not (content):
        abort(400)

    user_id = session.get('user_id')
    user = user_repository_singleton.get_user_by_id(user_id)

    if not (user_id and user and post_id):    
        abort(401)

    author_id = user.user_id
    new_comment = comment_repository_singleton.create_comment(content, timestamp, post_id, author_id)
    return redirect("/posts/"+ str(new_comment.post_id) + '#' + str(new_comment.comment_id))

# Delete comment
@app.post('/comments/<int:comment_id>/delete')
def delete_comment(comment_id: int):
    comment_to_delete = comment_repository_singleton.get_comment_by_id(comment_id)
    print(comment_to_delete)
    if not comment_to_delete:
        abort(404)
    
    comment_repository_singleton.delete_comment(comment_to_delete)
 
     #redirect to the referring page
    referrer = request.headers.get("Referer")
    if referrer:
        return redirect(referrer)
    else:
        return redirect('/')  #fallback to home if no referrer is found
    
# Edit comment
@app.get('/comments/<int:comment_id>/edit')
def edit_comment_form(comment_id: int):
    if 'user_id' not in session and 'username' not in session:
        abort(401)
    existing_comment = comment_repository_singleton.get_comment_by_id(comment_id)
    if not existing_comment:
        abort(404)
    if existing_comment.author_id != session.get('user_id'):
        abort(403)
    return render_template('edit_comment_form.html', existing_comment=existing_comment)

@app.post('/comments/<int:comment_id>')
def edit_comment(comment_id: int):
    content = request.form.get('content')
    if not content:
        abort(400)

    existing_comment = comment_repository_singleton.get_comment_by_id(comment_id)
    if not existing_comment:
        abort(401)

    comment_repository_singleton.edit_comment(existing_comment, content)
    
    return redirect("/posts/"+ str(existing_comment.post_id) + '#' + str(comment_id))


@app.post('/vote/post')
def handle_post_vote():
    data = request.json
    voter_id = session.get('user_id')

    if 'post_id' in data and 'vote_type' in data:
        post_id = data['post_id']
        vote_type = data['vote_type']
    else:
        return jsonify({'error': 'Invalid request'}), 400
    
    if not voter_id:
        return jsonify({'error': 'User not logged in'}), 401
    
    #TODO: Add way to verify there is only one vote per user for a post
    # if there are multiple THIS WILL NOT WORK
    # right now, it just queries the first from the database, future iterations should add some sort of rule to the database to
    # verify that only vote can be added to a post per user
    existing_vote = vote_repository_singleton.get_post_vote_by_post_and_user_ids(post_id, voter_id)
    if existing_vote:
        if (existing_vote.is_upvote and vote_type == 'down') or (not existing_vote.is_upvote and vote_type == 'up'):
            vote_repository_singleton.delete_post_vote_by_id(existing_vote.vote_id)
            net_votes = vote_repository_singleton.get_net_post_votes(post_id)
            #Vote not created, user already has a vote of the opposite type on this post, deleting this vote
            return jsonify({'message': 'Vote deleted', 'voteType': None, 'netVotes': net_votes}), 200
        #Vote not created, user already has a vote of this type on this post
        net_votes = vote_repository_singleton.get_net_post_votes(post_id)
        return jsonify({'error': 'Vote not changed', 'voteType': 'up' if existing_vote.is_upvote else 'down', 'netVotes': net_votes}), 409
    #User does not have a vote on this post, so creating a new one
    new_vote = vote_repository_singleton.create_post_vote(post_id, voter_id, vote_type == 'up')
    net_votes = vote_repository_singleton.get_net_post_votes(post_id)
    return jsonify({'message': 'Vote created', 'voteType': 'up' if vote_type == 'up' else 'down', 'netVotes': net_votes}), 201


@app.post('/vote/comment')
def handle_comment_vote():
    data = request.json
    voter_id = session.get('user_id')

    if 'comment_id' in data and 'vote_type' in data:
        comment_id = data['comment_id']
        vote_type = data['vote_type']
    else:
        return jsonify({'error': 'Invalid request'}), 400
    
    if not voter_id:
        return jsonify({'error': 'User not logged in'}), 401
    
    #TODO: Add way to verify there is only one vote per user for a post
    # if there are multiple THIS WILL NOT WORK
    # right now, it just queries the first from the database, future iterations should add some sort of rule to the database to
    # verify that only vote can be added to a post per user
    existing_vote = vote_repository_singleton.get_comment_vote_by_comment_and_user_ids(comment_id, voter_id)
    if existing_vote:
        if (existing_vote.is_upvote and vote_type == 'down') or (not existing_vote.is_upvote and vote_type == 'up'):
            vote_repository_singleton.delete_comment_vote_by_id(existing_vote.vote_id)
            net_votes = vote_repository_singleton.get_net_comment_votes(comment_id)
            #Vote not created, user already has a vote of the opposite type on this post, deleting this vote
            return jsonify({'message': 'Vote deleted', 'voteType': None, 'netVotes': net_votes}), 200
        #Vote not created, user already has a vote of this type on this post
        net_votes = vote_repository_singleton.get_net_comment_votes(comment_id)
        return jsonify({'error': 'Vote not changed', 'voteType': 'up' if existing_vote.is_upvote else 'down', 'netVotes': net_votes}), 409
    #User does not have a vote on this post, so creating a new one
    new_vote = vote_repository_singleton.create_comment_vote(comment_id, voter_id, vote_type == 'up')
    net_votes = vote_repository_singleton.get_net_comment_votes(comment_id)
    return jsonify({'message': 'Vote created', 'voteType': 'up' if vote_type == 'up' else 'down', 'netVotes': net_votes}), 201

def sort_posts_newest_to_oldest(posts):
    # Sort the posts list by the timestamp attribute in descending order
    sorted_posts = sorted(posts, key=lambda post: post.timestamp, reverse=True)
    return sorted_posts
