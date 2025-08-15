from flask import Flask, render_template, request, redirect, session, url_for
import pandas as pd
import joblib
import json
import random
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load trained model
model = joblib.load('model.pkl')

# Expected columns as per model training
EXPECTED_COLUMNS = [
    'age', 'hypertension', 'heart_disease', 'bmi', 'HbA1c_level', 'blood_glucose_level',
    'gender_Female', 'gender_Male',
    'smoking_history_current', 'smoking_history_non-smoker', 'smoking_history_past_smoker'
]

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password ="root",
                database="diabetes_prediction"
            )
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()
            cursor.close()
            connection.close()

            if user:
                session['user'] = username
                return redirect('/dashboard')
            else:
                return render_template('login.html', login_failed=True)

        except Exception as e:
            print("Login error:", e)
            return render_template('login.html', login_failed=True)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        mobile = request.form.get('mobile')

        try:
            connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root",
                database="diabetes_prediction"
            )
            cursor = connection.cursor()
            print("entered breadpoint one ")
            cursor.execute("INSERT INTO users (username, password, email, mobile) VALUES (%s, %s, %s, %s)",
                           (username, password, email, mobile))
            print("enter break point two")
            connection.commit()
            cursor.close()
            connection.close()
            return render_template('registration.html', registration_success=True)
        except Exception as e:
            print("Registration error:", e)
            return render_template('registration.html', registration_failed=True, error_message=str(e))
    return render_template('registration.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    result = None
    meal_plan = None
    exercise_plan = None

    if request.method == 'POST':
        if 'predict' in request.form:
            gender = request.form.get('gender')
            age = int(request.form.get('age') or 0)
            hypertension = int(request.form.get('hypertension') or 0)
            heart_disease = int(request.form.get('heart_disease') or 0)
            smoking_history = request.form.get('smoking_history')
            bmi = float(request.form.get('bmi') or 0)
            hba1c = float(request.form.get('hba1c') or 0)
            glucose = float(request.form.get('glucose') or 0)

            # Prepare raw input
            raw = {
                'gender': gender,
                'age': age,
                'hypertension': hypertension,
                'heart_disease': heart_disease,
                'smoking_history': smoking_history,
                'bmi': bmi,
                'HbA1c_level': hba1c,
                'blood_glucose_level': glucose
            }

            df = pd.DataFrame([raw])

            # One-hot encode gender and smoking_history
            df = pd.get_dummies(df, columns=['gender', 'smoking_history'])

            # Ensure all expected columns exist
            for col in EXPECTED_COLUMNS:
                if col not in df.columns:
                    df[col] = 0

            # Reorder columns to match model input
            df = df[EXPECTED_COLUMNS]

            # Predict
            prediction = model.predict(df)[0]
            result = "Positive" if prediction == 1 else "Negative"
            session['result'] = result

        elif 'generate_meal' in request.form:
            result = session.get('result', None)
            if result:
                try:
                    with open('meal_plan.json') as f:
                        plans = json.load(f)

                    key = 'diabetic' if result == "Positive" else 'non_diabetic'
                    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                    samples = random.choices(plans, k=7)

                    meal_plan = [
                        {
                            'day': day,
                            'breakfast': sample[key]['breakfast'],
                            'lunch': sample[key]['lunch'],
                            'snacks': sample[key]['snacks'],
                            'dinner': sample[key]['dinner']
                        }
                        for day, sample in zip(days, samples)
                    ]
                except Exception as e:
                    print("Meal/ Exercise plan error:", e)
       
        elif 'generate_exercise' in request.form:
            result = session.get('result', None)
            if result:
                try:
                    with open('exercise_plan.json') as f:
                        exercise_data = json.load(f)
                    key = 'diabetic_plan' if result == "Positive" else 'non_diabetic_plan'
                    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                    plan_sample = random.choice(exercise_data)
                    
                    exercise_plan = [
                        {
                            'day': day,
                            'exercise': plan_sample[key][day.lower()]
                        }
                        for day in days
                    ]
                except Exception as e:
                    print("Exercise plan error:", e)


    return render_template('dashboard.html', result=result, meal_plan=meal_plan, exercise_plan=exercise_plan, username=session['user'])


if __name__ == '__main__':
    app.run(debug=True)
