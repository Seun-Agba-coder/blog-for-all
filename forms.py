from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField



# WTForm for creating a blog post
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")

# Creates a RegisterForm to register new users
# layout of resister form
class RegisterForm(FlaskForm):
    name = StringField(label="name", validators=[DataRequired()])
    email = EmailField(label='email', validators=[DataRequired()])
    password = PasswordField(label="password", validators=[DataRequired()])
    submit = SubmitField(label="Sign me up!")


# Creates a LoginForm to login existing users
class LoginForm(FlaskForm):
    email = EmailField(label='email', validators=[DataRequired()])
    password = PasswordField(label="password", validators=[DataRequired()])
    submit = SubmitField(label="LET ME IN!")


# Creates a CommentForm so users can leave comments below posts
class CommentForm(FlaskForm):
    comment = CKEditorField(label='comment', validators=[DataRequired()])
    sumit = SubmitField(label="submit comment")