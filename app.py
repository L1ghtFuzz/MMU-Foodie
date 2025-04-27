from flask import Flask, render_template, redirect, request
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# My App
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)


#Data Class ~ Row of data
class MyAdmin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)

    def __repr__(self):
        return super().__repr__()


# Routes to Webpages
# Home page
@app.route("/", methods=["POST", "GET"])
def home():
    # Add Admin
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        new_admin = MyAdmin(username=username, password=password)
        try:
            db.session.add(new_admin)
            db.session.commit()
            return redirect("/")
        except Exception as e:
            return f"ERROR: {e}"
    else:
        admin = MyAdmin.query.all()
        return render_template('login-form.html', admin=admin)


# Delete an item
@app.route("/delete/<int:id>")
def delete(id:int):
    delete_admin = MyAdmin.query.get_or_404(id)
    try: 
        db.session.delete(delete_admin)
        db.session.commit()
        return redirect("/")
    except Exception as e:
        return f"ERROR:{e}"


# Edit an item
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id:int):
    admin = MyAdmin.query.get_or_404(id)
    if request.method == "POST":
        admin.content = request.form['content']
        try:
            db.session.commit()
            return redirect("/")
        except Exception as e:
            return f"Error:{e}"
        
    else:
        return render_template('edit.html', admin=admin)



# Runner and Debugger
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)