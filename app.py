from flask import Flask, session, redirect, url_for, escape, request, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

app=Flask(__name__)
app.secret_key='abbas'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assignment3.db'
app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)

# Check if logged in.
def logged_in():
	return 'utorid' in session

@app.route('/')
def index():
	if(not logged_in()):
		return redirect(url_for('login'))
	return render_template('index.html')

# Route that deals with remarking. Students can POST mark remark requests.
# Instructors can GET all outstanding requests and POST mark updates to students.
@app.route('/remark', methods=['GET', 'POST'])
def remark():
	if(not logged_in()):
		return redirect(url_for('login'))

	sql = "SELECT user_type FROM users WHERE utorid='{}'".format(session['utorid'])
	results = db.engine.execute(text(sql))
	user_type = ''
	for result in results:
		user_type = result['user_type']

	if request.method == 'POST':
		if user_type == 'student':
			utorid = session['utorid']
			# The name of the assignment to be remarked.
			assignment = request.form['assignment']
			# The reason for remark.
			reasons = request.form['reasons']
			sql = "INSERT INTO remarks VALUES ('{}', '{}', '{}')".format(utorid, assignment, reasons)
			db.engine.execute(text(sql).execution_options(autocommit=True))
			return redirect(url_for('dashboard'))

		elif user_type == 'instructor':
			# THIS IS IN JSON, when the request is made, set mimetype to 'application/json'
			# The format will look like:
			'''
			{
			  "remark": [
			    {
			      "utorid":"wangy841",
			      "marks": {
			          "a1":1,
			          "a2":2,
			          "a3":3,
			          "midterm":1,
			          "final": 100
			      }
			    },
			    {
			      "utorid":"wangy842",
			      "marks": {
			          "a1":2,
			          "a2":3,
			          "a3":4,
			          "midterm":2,
			          "final": 99
			      }
			    }
			  ]
			}
			'''
			data = request.get_json()
			remark_requests = data['remarks']

			# Build the update query.
			for remark_request in remark_requests:
				utorid = remark_request['utorid']
				sql = "UPDATE marks SET "
				for assignment in remark_request['marks']:
					sql += assignment + " = " + remark_request['marks'][assignment] + ", "
				sql = sql[:-2] + " WHERE utorid='{}'".format(utorid)
				db.engine.execute(text(sql).execution_options(autocommit=True))

			return redirect(url_for('dashboard'))


# Route that deals with dashboard info.
# Students should be able to see their marks and send remarks for their assignments.
# Instructors should see the marks of every student and also see a list of pending remarks.

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
	if(not logged_in()):
		return redirect(url_for('login'))

	# Get the user type.
	sql = "SELECT user_type FROM users WHERE utorid='{}'".format(session['utorid'])
	results = db.engine.execute(text(sql))

	user_type = ''
	for result in results:
		user_type = result['user_type']

	if user_type == 'student':
		# Get all marks that belong to the current student.
		sql = "SELECT * FROM marks WHERE utorid='{}'".format(session['utorid'])
		results = db.engine.execute(text(sql))
		marks_column = list(results.keys())
		marks = []
		for result in results:
			marks = result
		result_marks = []
		for i in range(len(marks_column)):
			if(marks_column[i] != 'utorid'):
				result_marks.append((marks_column[i], marks[i]))

		sql = "SELECT name FROM users WHERE utorid='{}'".format(session['utorid'])
		results = db.engine.execute(text(sql))

		for result in results:
			name = result[0]

		# Return data is a list of tuples [(a1, mark1), (a2, mark2), ... ]
		return render_template('dashboard_student.html', data=result_marks, name=name)

	# Instructor user
	elif user_type == 'instructor':

		if request.method == 'GET':
			sql = "SELECT * FROM marks"
			results = db.engine.execute(text(sql))

			all_marks = []
			for result in results:
				all_marks.append(result)


			sql = "SELECT name FROM users WHERE utorid='{}'".format(session['utorid'])
			results = db.engine.execute(text(sql))

			for result in results:
				name = result[0]

			sql = "SELECT * FROM remarks"
			results = db.engine.execute(text(sql))

			all_remarks = []
			for result in results:
				all_remarks.append(result)

			# Return is a list of tuples, first item is column names.
			# 2nd+ items are the marks of all the students.
			# [(utorid, a1, a2, ...), (wangy841, 16, 90, ..) ...]
			return render_template('dashboard_instructor.html', data=all_marks, name=name, remarks=all_remarks)

# Route that deals with student feedback.
# Students can POST feedback at this URL and instructors can GET feedback from students.

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
	if(not logged_in()):
		return redirect(url_for('login'))

	# Get the user type.
	sql = "SELECT user_type FROM users WHERE utorid='{}'".format(session['utorid'])
	results = db.engine.execute(text(sql))
	user_type = ''
	for result in results:
		user_type = result['user_type']

	# Student user
	if user_type == 'student':
		if(request.method == 'GET'):
			sql = "SELECT name, utorid FROM users WHERE user_type='instructor'"
			results = db.engine.execute(text(sql))
			instructors = []
			for result in results:
				instructors.append((result['name'], result['utorid']))

			return render_template('feedback_student.html', data=instructors)

		elif(request.method == 'POST'):
			student_id = session['utorid']
			instructor_id = request.form['instructor_id']
			feedback = request.form['feedback']
			sql = "INSERT INTO feedback VALUES ('{}', '{}', '{}')".format(instructor_id, student_id, feedback)
			db.engine.execute(text(sql).execution_options(autocommit=True))
			return redirect(url_for('feedback'))

	# Instructor user
	elif user_type == 'instructor':
		sql = "SELECT * FROM feedback WHERE instructor_id='{}'".format(session['utorid'])
		results = db.engine.execute(text(sql))
		feedback = []
		for result in results:
			feedback.append((result['student_id'], result['feedback']))

		# Return data is a list of tuples [(utorid, feedback)]
		return render_template('feedback_instructor.html', data=feedback)

# Login route
@app.route('/login',methods=['GET','POST'])
def login():
	# Login request
	if request.method=='POST':
		sql = 'SELECT * FROM users'
		results = db.engine.execute(text(sql))
		for result in results:
			if result['utorid']==request.form['utorid']:
				if result['password']==request.form['password']:
					# Login successful.
					session['utorid']=request.form['utorid']
					return redirect(url_for('index'))

		return render_template('login.html', login="failed")

	# Return login page.
	else:
		return render_template('login.html')

# Signup route.
@app.route('/signup', methods=['GET', 'POST'])
def signup():
	if request.method == 'POST':
		# This request takes the parameters utorid, name, and password
		utorid = request.form['utorid']
		name = request.form['name']
		password = request.form['password']
		type = request.form['user_type'].lower()
		sql = "INSERT INTO users VALUES ('{}', '{}', '{}', '{}')".format(utorid, name, password, type)
		db.engine.execute(text(sql).execution_options(autocommit=True))
		if(type == 'student'):
			sql = "INSERT INTO marks VALUES ('{}', NULL, NULL, NULL, NULL, NULL)".format(utorid)
			db.engine.execute(text(sql).execution_options(autocommit=True))

		return redirect(url_for('login'))
	elif request.method == 'GET':
		return render_template('signup.html')

@app.route('/logout')
def logout():
	session.pop('utorid', None)
	return redirect(url_for('login'))


@app.route('/assignments')
def assignments():
	if(not logged_in()):
		return redirect(url_for('login'))
	return render_template('assignments.html')

@app.route('/course_team')
def team():
	if(not logged_in()):
		return redirect(url_for('login'))
	return render_template('course_team.html')

@app.route('/labs')
def labs():
	if(not logged_in()):
		return redirect(url_for('login'))
	return render_template('labs.html')

@app.route('/syllabus')
def syllabus():
	if(not logged_in()):
		return redirect(url_for('login'))
	return render_template('syllabus.html')

if __name__=="__main__":
	app.run(debug=True,host='0.0.0.0')
