from flask import Flask, render_template, request
from frontend.backend.qa_chatbot_code import chatbot 

app = Flask(__name__)

@app.route("/")
def index():
  return render_template("index.html")

@app.route("/query_results", methods=["POST"])
def query_results():
  response, iframe_url = chatbot(request.form["query"])
  return render_template("results.html", response=response, iframe_url=iframe_url)

if __name__ == "__main__":
  app.run(debug=True)