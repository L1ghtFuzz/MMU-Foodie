from flask import Flask

app = Flask(__name__)



@app.route('/mysite')
def hello():
    return "Hello,world!"

