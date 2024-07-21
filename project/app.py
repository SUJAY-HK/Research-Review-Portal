import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(80), nullable=False)  # 'user' or 'admin'

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    paper_name = db.Column(db.String(80), nullable=False)
    document_submission = db.Column(db.String(200), nullable=False)
    feedback = db.Column(db.String(200))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['logged_in'] = True
            session['user_id'] = user.id
            session['role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    if session['role'] != 'user':
        return redirect(url_for('admin_dashboard'))
    user_id = session['user_id']
    documents = Document.query.filter_by(user_id=user_id).all()
    return render_template('user_dashboard.html', documents=documents)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if session['role'] != 'admin':
        return redirect(url_for('user_dashboard'))
    documents = Document.query.all()
    return render_template('admin_dashboard.html', documents=documents)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if session['role'] != 'user':
        return redirect(url_for('admin_dashboard'))
    if 'document_submission' not in request.files:
        return redirect(request.url)
    file = request.files['document_submission']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user_id = session['user_id']
        name = request.form['name']
        paper_name = request.form['paper_name']
        new_document = Document(user_id=user_id, name=name, paper_name=paper_name, document_submission=filename)
        db.session.add(new_document)
        db.session.commit()
        return redirect(url_for('user_dashboard'))
    return redirect(request.url)

@app.route('/feedback/<int:doc_id>', methods=['POST'])
@login_required
def feedback(doc_id):
    if session['role'] != 'admin':
        return redirect(url_for('user_dashboard'))
    document = Document.query.get_or_404(doc_id)
    feedback = request.form['feedback']
    document.feedback = feedback
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    if session['role'] != 'admin':
        return redirect(url_for('user_dashboard'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
    app.run(debug=True)
