from flask_wtf import FlaskForm
from wtforms import RadioField, TextField
from wtforms.validators import InputRequired, Length

class NewGame(FlaskForm):
    gamename = TextField("Game name", [InputRequired(), Length(max=20,min=1)])    