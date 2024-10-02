from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from email.mime.text import MIMEText
from dotenv import load_dotenv
from smtplib import SMTP_SSL
import os



app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap5(app)

# loads environment variables into script
load_dotenv()

# Configure Flask-Login

# initialize the login manager
login_manager = LoginManager()
# configures login manager with app
login_manager.init_app(app)


# user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DB_URI", "sqlite:///blog.db")


db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES

#  Create a User table for all your registered users.
# configures Use table
class User(UserMixin, db.Model):
    # Gives the class it table name
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(250), nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts: Mapped[list['BlogPost']] = relationship(back_populates="author")

    # This will act like a List of Comment objects attached to each User.
    # The "comment_author" refers to the comment_author property in the BlogPost class.
    comments: Mapped[list['Comment']] = relationship(back_populates='comment_author')

# CREATES THE BLOGPOST TABLE
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    # Create reference to the User object. The "posts" refers to the posts property in the User class.
    author: Mapped["User"] = relationship(back_populates="posts")

    # This will act like a List of Comment objects attached to a blog_post.
    # "post" refers to the post property in the Comment class.
    comments: Mapped[list['Comment']] = relationship(back_populates="post")

    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


# Creates the comment table in the database
class Comment(db.Model):
    ___tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User)
    # "comments" refers to the comments property in the User class.
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    comment_author: Mapped['User'] = relationship(back_populates="comments")

    # Create Foreign Key, "Blog_posts.id" the users refers to the tablename of BlogPost
    blog_id: Mapped[int] = mapped_column(Integer, ForeignKey("blog_posts.id"))
    # "comment" refers to the comments property in the BlogPost class.
    post: Mapped["BlogPost"] = relationship(back_populates="comments")

    text: Mapped[str] = mapped_column(Text, nullable=False)


def send_email(name, email, phone_number, message):
    """Sends the message written by the User on the contact form to my email via the companies email"""
    RECIPIENT_EMAIL = os.getenv("RECEIVER_EMAIL")
    COMPANY_PASSWORD = os.getenv("COMPANY_EMAIL_PASSWORD")
    COMPANY_EMAIL = os.getenv("COMPANY_EMAIL")

    subject = "A Blog User Contacted"
    body = f"Name: {name}\n Email: {email}\n Phone Number: {phone_number}\n message: {message}"
    # initialize MimeText
    message = MIMEText(body, _subtype="plain")
    # sets the necessary variable for the email head
    message["Subject"] = subject
    message["From"] = COMPANY_EMAIL
    message["To"] = RECIPIENT_EMAIL

    with SMTP_SSL(host="smtp.gmail.com", port=465) as connection:
        connection.login(user=COMPANY_EMAIL, password=COMPANY_PASSWORD)
        connection.sendmail(from_addr=COMPANY_EMAIL,
                            to_addrs=RECIPIENT_EMAIL,
                            msg=message.as_string())

    return True

with app.app_context():
    db.create_all()

# initialize  Gravatar with the application
# For adding profile images to the comment section
gravatar = Gravatar(app,
                   size=100,
                   rating='g',
                   default='retro',
                   force_default=False,
                   force_lower=False,
                   use_ssl=False,
                   base_url=None)


# decorator function to only allow commentors to delete comment
def commentors(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        # Checks if the current_user has a comment in the Comment table if so allows for the comment to be
        # deleted
        commentor = db.session.execute(db.select(Comment).where(Comment.user_id == current_user.id)).scalar()
        if commentor is not None or current_user.id == 1:
            return function(*args, **kwargs)
        else:
            return abort(403)
    return wrapper_function


# A decorator function to be implemented on some route to restrict access to users that are not the admin.

def admin_only(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        # if id is 1  then continue with the route function
        if current_user.get_id() == '1':
            return function(*args, **kwargs)
        # return abort with 403 error
        else:
            return abort(403)
    return wrapper_function


# Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['GET','POST'])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        # Checks if user email address is already on the database if so redirects back to the login page
        user_exist = db.session.execute(db.select(User).where(User.email == register_form.email.data)).scalar()
        if user_exist:
            flash("You've already signed up with that email, log in instead", 'flash')
            return redirect(url_for('login'))
        hashed_password = generate_password_hash(register_form.password.data, method="pbkdf2:sha256", salt_length=8)
        new_user = User(
            name=register_form.name.data,
            email=register_form.email.data,
            password=hashed_password,
        )
        db.session.add(new_user)
        db.session.commit()

        # logs in a user into the website
        login_user(new_user)

        # redirects to the home page
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=register_form)


# Retrieve a user from the database based on their email.
@app.route('/login', methods=['POST', 'GET'])
def login():
    login_form = LoginForm()
    # if user submits checks if credentials are in the database if not redirects back to get_all_post page
    if login_form.validate_on_submit():
        user_exist = db.session.execute(db.select(User).where(User.email == login_form.email.data)).scalar()

        if user_exist:
            if check_password_hash(user_exist.password, login_form.password.data):
                login_user(user_exist)
                return redirect(url_for('get_all_posts'))

            else:
                flash('Invalid password provided. Please try again.', 'error')
                return redirect(url_for('login'))

        else:
            flash('Register with us first', 'error')
            return redirect(url_for('register'))

    return render_template("login.html", form=login_form)


@app.route('/logout')
def logout():
    # logs a user out of the session
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("Please login first before being able to comment", category="flash")
            return redirect(url_for("login"))

        # Adds a user comment into the database. also need to pass the parameter of current user and requested_post
        # to the "comment_author" and "post" to tell the Comment table which user and blog the comment
        # belongs too.

        new_comment = Comment(
            text=comment_form.comment.data,
            comment_author=current_user,
            post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, form=comment_form)


# Uses a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# Uses a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)



# Uses a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["POST", "GET"])
def contact():
    message_sent = False
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone_number = request.form["phone"]
        message = request.form["message"]
        if not current_user.is_authenticated:
            # redirects to login page
            flash('Login before trying to contact the blog admin', 'flash')
            return redirect(url_for("login"))

        # if so sends message to admin
        message_sent = send_email(name=name, email=email, phone_number=phone_number, message=message)
    return render_template("contact.html", msg_sent=message_sent)

@app.route("/delete_comment")
@commentors
def delete_comment():
    """ Allows a user who posted a comment to delete it"""
    user_comment = request.args.get("user_comment")
    blog_id = request.args.get("blog_id")
    delete_comment = db.get_or_404(Comment, user_comment)
    db.session.delete(delete_comment)
    db.session.commit()

    return redirect(url_for("show_post", post_id=blog_id))



if __name__ == "__main__":
    app.run(debug=False)
