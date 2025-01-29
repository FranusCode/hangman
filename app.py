from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random, os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'developerskie')
app.config['SECURITY_PASSWORD_SALT'] = os.environ.get('SECURITY_PASSWORD_SALT', 'jakas-sol')

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    correct_words = db.Column(db.Integer, default=0)
    correct_word_history = db.Column(db.Text, default="")

    def set_password(self, password):
        self.password = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def add_correct_word(self, word):
        if self.correct_word_history:
            self.correct_word_history += f", {word}"
        else:
            self.correct_word_history = word
        self.correct_words += len(word)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        if 'word' not in session:
            random_word = get_random_word()
            session['category'] = random_word[0]
            session['word'] = random_word[1]
            session['guesses'] = []
            session['misses'] = 0
            session['message'] = 'Click letter and enter to start'
        word_display = ''.join([letter if letter in session['guesses'] else ' _ ' for letter in session['word']])

        session.pop('play_sound', None)

        return render_template('index.html', 
                            category = session['category'],
                            word_display=word_display, 
                            guesses=session['guesses'], 
                            misses=session['misses'], 
                            message=session['message'], 
                            image=f"images/hangman{session['misses'] + 1}.png",
                            user = current_user.username)
    else:
        return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check your username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('category', None)
    session.pop('word', None)
    session.pop('guesses', None)
    session.pop('misses', None)
    session.pop('message', None)
    session.pop('game_status', None)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/reset')
@login_required
def reset():
    session.pop('category', None)
    session.pop('word', None)
    session.pop('guesses', None)
    session.pop('misses', None)
    session.pop('message', None)
    session.pop('game_status', None)
    return redirect(url_for('index'))

@app.route('/stats')
@login_required
def stats():
    return render_template('stats.html', 
                           correct_word_history=current_user.correct_word_history.split(', '), 
                           score = current_user.correct_words, 
                           user = current_user.username)

@app.route('/guess', methods=['GET', 'POST'])
@login_required
def guess():
    guess = request.form['guess'].upper()
    if guess not in session['guesses']:
        session['guesses'].append(guess)
        if guess in session['word']:
            session['message'] =  f"Good Guess! '{guess}' is in the word!"
        else:
            session['misses'] += 1
            session['message'] = f"Sorry! '{guess}' is not in the word!"
    else:
        session['message'] = f"You already guessed '{guess}'."
    
    if all(letter in session['guesses'] for letter in session['word']):
        current_user.add_correct_word(session['word'])
        session['message'] = f"Congratulations! correct!"
        session['game_status'] = 'won'
        session['guesses'] = []
        session['misses'] = 0

    elif session['misses'] >= 6:
        session['game_status'] = 'lost'
        session['message'] = f"The word was {session['word']}"
        session['guesses'] = []
        session['misses'] = 0

    return redirect(url_for('index'))

def get_random_word():
    pliki = [f for f in os.listdir("./static/words") if os.path.isfile(os.path.join("./static/words", f))] 
    
    losowy_plik = random.choice(pliki)
    sciezka = os.path.join(os.getcwd(), "./static/words", losowy_plik)

    with open(sciezka, "r", encoding="utf-8") as plik:
        zawartosc = plik.read()

    zawartosc = zawartosc.strip().split(', ')

    index = random.randint(0, len(zawartosc) - 1)
    category = losowy_plik[:-4].upper()
    return [category, zawartosc[index].upper()]

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5002, debug=True)
